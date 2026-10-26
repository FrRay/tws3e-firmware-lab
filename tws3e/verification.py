"""Independent decompression, original-instruction checks and negative controls."""
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import zlib
from .core import audit, official, parse, require


def cross_check(original, candidate, scale, sevenzip='7z'):
    report = audit(original, candidate, scale)
    a, b = official(original), parse(candidate)
    exe = shutil.which(sevenzip)
    require(exe is not None, '7-Zip not found: install it or pass --sevenzip /path/to/7z')
    from .emulation import Machine, NativeCRC, original_validators, verify, BASE, u32
    import unicorn
    versions = subprocess.run([exe, 'i'], capture_output=True, check=True)
    with tempfile.TemporaryDirectory(prefix='tws3e_check_') as directory:
        file = Path(directory)/'block.lzma'
        for stream, expected in zip(a.streams+b.streams, a.blocks+b.blocks):
            file.write_bytes(stream)
            decoded = subprocess.run([exe, 'x', '-so', str(file)], capture_output=True, check=True).stdout
            require(decoded == expected, 'Independent 7-Zip output mismatch')
    require(original_validators(a.image, candidate) == [1, 1], 'Original application validators rejected candidate')
    crc = NativeCRC(a.image)
    require(crc.update(b'123456789') == 0xcbf43926, 'Native CRC known vector failed')
    native = verify(candidate, crc)
    bad = bytearray(candidate)
    bad[1000] ^= 1
    try:
        verify(bad, crc)
    except ValueError:
        pass
    else:
        raise ValueError('Native CRC failed to reject corruption')
    # A matching CRC is not enough: original application functions also reject
    # damaged magic and an image length above the platform's stated capacity.
    bad_magic = bytearray(candidate)
    bad_magic[:4] = b'xxxx'
    require(original_validators(a.image, bad_magic) == [0, None], 'Bad magic was accepted')
    bad_length = bytearray(candidate)
    struct.pack_into('<I', bad_length, 0x20, 0x20c001)
    require(original_validators(a.image, bad_length) == [0, None], 'Oversize image was accepted')
    m = Machine(a.image)
    m.uc.mem_write(BASE, b.image)
    m.uc.mem_write(0x20007a60, b.image[0x1c3d6c:0x1c3d6c+0x1844])
    m.uc.mem_write(0x20007b08, u32(0))
    m.uc.mem_write(0x2000cd3c, u32(1))
    m.uc.mem_write(0x2000cc34, u32(1))
    actual_scale = struct.unpack_from('<f', b.image, 0x1c3e20)[0]
    executions = []
    for gain in (0, 128, 250, 256, 511, 512):
        expected = int(struct.unpack('<f', struct.pack('<f', gain*actual_scale))[0])
        for _ in range(3):
            require(m.run(0x4122c, gain, gain, 1) == 0, 'FF setter failed')
            require(m.word(0x2000cd44) == expected, 'FF result mismatch')
        require(m.run(0x4122c, gain, gain, 2) == 0 and m.word(0x2000cc3c) == gain, 'FB path changed')
        executions.append(dict(input_q9=gain, ff_staged_q9=expected, fb_staged_q9=gain))
    report.update(independent_7zip_streams=20, application_validators=[1, 1],
                  native_crc=native, original_gain_setter_executions=executions,
                  negative_controls=['payload bit flip rejected', 'bad magic rejected', 'oversize image rejected'],
                  environment=dict(python=platform.python_version(), unicorn=unicorn.__version__,
                                   zlib=zlib.ZLIB_RUNTIME_VERSION,
                                   sevenzip=versions.stdout.decode(errors='replace').splitlines()[:4]),
                  checks_complete=True,
                  limits=['Synthetic RAM and intercepted IO; no real Flash, bootloader or radio.',
                          'No acoustic-stability, signature-bypass or recovery claim.'])
    return report
