"""Execute selected user-supplied original routines in synthetic memory only.

Logger, CRC callback and IO hooks in the application-validator checks are stubs.
The native CRC check separately executes the actual CRC instructions. Gain checks
leave the hardware output map at zero. No Bluetooth, Flash or physical IO.
"""
import re
import lzma
import struct
import zlib
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import *
from .core import IMAGE_SHA, require, sha

BASE = 0x2c010000
RAM = 0x20000000
AUD = 0x283ee000

def u32(value):
    return struct.pack('<I', value)

class Machine:
    def __init__(self, image):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        self.uc.mem_map(BASE, 0x200000)
        self.uc.mem_write(BASE, image)
        self.uc.mem_map(RAM, 0x80000)
        self.uc.mem_map(AUD, 0x10000)
        self.uc.mem_map(0xe000e000, 0x2000)
        self.uc.mem_write(0xe000ed88, u32(0xf << 20))
        self.uc.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
        self.uc.reg_write(UC_ARM_REG_SP, RAM + 0x70000)
        self.stop = BASE + 0x1ff000
        self.uc.reg_write(UC_ARM_REG_LR, self.stop | 1)
        # Original startup initialized-data copy.
        source = 0x2c1d3d6c - BASE
        self.uc.mem_write(0x20007a60, image[source:source + (0x200092a4 - 0x20007a60)])
        self.hooks = {}
        self.uc.hook_add(UC_HOOK_CODE, self._hook)
        self.stub(0x171708, lambda uc: None)  # diagnostic logger
        self.stub(0x26f70, self._assertion)
        self.stub(0x3dc68, self._assertion)

    @staticmethod
    def _assertion(uc):
        raise AssertionError(f'Firmware assertion at LR={uc.reg_read(UC_ARM_REG_LR):08x}')

    def _hook(self, uc, address, size, _):
        callback = self.hooks.get(address)
        if callback is not None:
            callback(uc)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def stub(self, offset, callback):
        self.hooks[BASE + offset] = callback

    def word(self, address):
        return struct.unpack('<I', self.uc.mem_read(address, 4))[0]

    def run(self, offset, *arguments):
        self.uc.reg_write(UC_ARM_REG_SP, RAM + 0x70000)
        self.uc.reg_write(UC_ARM_REG_LR, self.stop | 1)
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), arguments):
            self.uc.reg_write(reg, value)
        self.uc.emu_start((BASE + offset) | 1, self.stop, count=200000)
        require(self.uc.reg_read(UC_ARM_REG_PC) == self.stop, 'Routine did not return within instruction limit')
        return self.uc.reg_read(UC_ARM_REG_R0)


def original_validators(image, data):
    m = Machine(image)
    flash = 0x2821c000
    m.uc.mem_map(flash, 0x120000)
    m.uc.mem_write(flash, bytes(data))
    table = 0x20060000
    m.uc.mem_write(0x20040d90, u32(0x20061000))  # platform-provided CRC table buffer
    m.stub(0x156a1c, lambda uc: uc.reg_write(UC_ARM_REG_R0, table))
    m.stub(0x14b31c, lambda uc: uc.reg_write(UC_ARM_REG_R0, 1))
    # Platform callback table: capacity, storage pointer, CRC, erase request.
    # Execute actual constant-returning platform callbacks, translating the code alias.
    for slot in (0x3c, 0x70, 0x44, 0x40):
        pointer = struct.unpack_from('<I', image, 0x1bcaa0 + slot)[0]
        m.uc.mem_write(table + slot, u32(pointer + 0x20000000))
    for slot, off in [(0x18, 0x1fe120), (0x28, 0x1fe124)]:
        m.uc.mem_write(table + slot, u32(BASE + off + 1))
    m.stub(0x1fe120, lambda uc: None)  # no actual erase or write

    def crc(uc):
        seed, address, size = [uc.reg_read(r) for r in
                              (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        uc.reg_write(UC_ARM_REG_R0, zlib.crc32(bytes(uc.mem_read(address, size)), seed))

    def copy(uc):
        dst, src, size = [uc.reg_read(r) for r in
                         (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        uc.mem_write(dst, bytes(uc.mem_read(src, size)))

    m.stub(0x1fe124, crc)
    m.stub(0x171418, copy)
    initial = m.run(0x1559f0, flash)
    complete = m.run(0x155bf4) if initial else None
    return [initial, complete]


class NativeCRC:
    def __init__(self, image):
        require(sha(image) == IMAGE_SHA, 'Native CRC requires original source image')
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB|UC_MODE_MCLASS)
        self.uc.mem_map(BASE, 0x200000)
        self.uc.mem_write(BASE, image)
        self.uc.mem_map(RAM, 0x80000)
        self.stop = BASE+0x1ff000

    def update(self, data, seed=0):
        for off in range(0, len(data), 16384):
            chunk = data[off:off+16384]
            self.uc.mem_write(RAM+0x10000, bytes(chunk))
            for reg, value in ((UC_ARM_REG_R0,seed),(UC_ARM_REG_R1,RAM+0x10000),
                               (UC_ARM_REG_R2,len(chunk)),(UC_ARM_REG_SP,RAM+0x70000),
                               (UC_ARM_REG_LR,self.stop|1)):
                self.uc.reg_write(reg,value)
            self.uc.emu_start((BASE+0x12c974)|1,self.stop,count=200000)
            require(self.uc.reg_read(UC_ARM_REG_PC)==self.stop, 'Native CRC instruction limit exceeded')
            seed = self.uc.reg_read(UC_ARM_REG_R0)
        return seed


def verify(data, crc):
    n = struct.unpack_from('<H',data,0x2e)[0]
    values = struct.unpack_from(f'<{n}I',data,0x30)
    payload = data[512:]
    calculated, seed = [], 0
    for off in range(0,len(payload),65536):
        seed = crc.update(payload[off:off+65536],seed)
        calculated.append(seed)
    require(list(values[:-1]) == calculated, 'Native cumulative CRC mismatch')
    require(values[-1] == sum(calculated)&0xffffffff, 'Native table sum mismatch')
    require(seed == struct.unpack_from('<I',data,8)[0], 'Native payload CRC mismatch')
    trailer = re.search(rb'CRC32_OF_IMAGE=0x[0-9a-fA-F]{8}$',data)
    cursor, blocks = 516, []
    while cursor < trailer.start():
        size = struct.unpack_from('>I',data,cursor)[0]
        blocks.append(lzma.decompress(data[cursor+4:cursor+4+size],format=lzma.FORMAT_ALONE))
        cursor += 4+size
    require(cursor == trailer.start(), 'Native check: container boundary mismatch')
    image = b''.join(blocks)
    marker = re.search(rb'CRC32_OF_IMAGE=0x([0-9a-fA-F]{8})',image)
    inner = crc.update(image[:marker.start(1)])
    require(inner == int(marker.group(1),16), 'Native internal CRC mismatch')
    full = crc.update(image[marker.start(1):],inner)
    require(full == struct.unpack_from('<I',data,0x24)[0], 'Native image CRC mismatch')
    return dict(payload_crc=hex(seed),image_crc=hex(full),inner_crc=hex(inner),
                native_cumulative_crc_entries=len(calculated),all_native_crc_checks_pass=True)
