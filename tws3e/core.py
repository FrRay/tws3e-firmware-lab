"""Observed oviV container, strict single-release editing, and byte auditing."""
from dataclasses import dataclass
import hashlib
import lzma
import math
from pathlib import Path
import re
import struct
import zlib

OFFICIAL_SHA = '8c83d3492e1a45b1240f5e15e2a2a46745b0954fb123a17af9b102bd96fb4182'
IMAGE_SHA = '1ea9859c1dc37a0716b8383958d03180e4a5a41c8acffedbfc208f1cbb08006b'
SCALE_OFFSET = 0x1c3e20
SCALES = (0.5, 0.99, 1.0, 1.01, 1.25, 1.5)
MARKER = rb'CRC32_OF_IMAGE=0x([0-9A-Fa-f]{8})'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def crc_values(payload):
    values = [zlib.crc32(payload[:end]) for end in range(65536, len(payload), 65536)]
    values.append(zlib.crc32(payload))
    return values + [sum(values) & 0xffffffff]


@dataclass
class Firmware:
    raw: bytes
    image: bytes
    blocks: list
    streams: list
    trailer: bytes
    crc_span: tuple

    def summary(self):
        return dict(sha256=sha(self.raw), bytes=len(self.raw), image_sha256=sha(self.image),
                    image_bytes=len(self.image), blocks=len(self.blocks),
                    project_field=u32(self.raw, 0x10), destination_fields=[u32(self.raw, x) for x in (0x18, 0x1c)],
                    cumulative_crc_count=struct.unpack_from('<H', self.raw, 0x2e)[0]-1,
                    crc_checks='passed; not a digital signature or device-boot test')


def parse(raw):
    require(540 <= len(raw) <= 0x11f000, 'Unsupported container size')
    require(raw[:4] == b'oviV', 'Expected oviV container; QCC APPUHDR5 is incompatible')
    payload = raw[512:]
    require(u32(raw, 4) == len(payload), 'Payload length mismatch')
    require(u32(raw, 8) == zlib.crc32(payload), 'Payload CRC mismatch')
    count = struct.unpack_from('<H', raw, 0x2e)[0]
    require(2 <= count <= 65 and 0x30+4*count <= 512, 'Invalid cumulative CRC count')
    values = crc_values(payload)
    require(count == len(values), 'Cumulative CRC count mismatch')
    require(list(struct.unpack_from(f'<{count}I', raw, 0x30)) == values, 'Cumulative CRC table/sum mismatch')
    require(payload[:4] == b'\xff'*4, 'Unexpected container marker')
    trailer = re.search(MARKER + rb'$', raw)
    require(trailer is not None, 'Missing outer trailer')
    cursor, total, blocks, streams = 516, 0, [], []
    while cursor < trailer.start():
        require(cursor+4 <= trailer.start(), 'Truncated stream size')
        size = struct.unpack_from('>I', raw, cursor)[0]
        end = cursor+4+size
        require(13 <= size and end <= trailer.start(), 'Invalid stream boundary')
        stream = raw[cursor+4:end]
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=64*1024*1024)
        block = decoder.decompress(stream, max_length=0x30001)
        require(decoder.eof and not decoder.unused_data and 0 < len(block) <= 0x30000,
                'Invalid/oversize LZMA block')
        total += len(block)
        require(total <= 0x20c000, 'Image exceeds observed platform capacity')
        streams.append(stream)
        blocks.append(block)
        cursor = end
    require(cursor == trailer.start() and bool(blocks), 'Container boundary mismatch')
    require(all(len(b) == 0x30000 for b in blocks[:-1]), 'Unexpected nonfinal block size')
    image = b''.join(blocks)
    require(u32(raw, 0x20) == len(image), 'Image length mismatch')
    require(u32(raw, 0x24) == zlib.crc32(image), 'Image CRC mismatch')
    marker = re.search(MARKER, image)
    require(marker is not None, 'Missing internal sanity CRC')
    require(zlib.crc32(image[:marker.start(1)]) == int(marker.group(1), 16), 'Internal sanity CRC mismatch')
    return Firmware(raw, image, blocks, streams, raw[trailer.start():], marker.span(1))


def official(raw):
    require(sha(raw) == OFFICIAL_SHA, 'Unsupported source SHA-256: editing is bound to the identified official v2.6.3')
    fw = parse(raw)
    require(sha(fw.image) == IMAGE_SHA and len(fw.blocks) == 10, 'Source profile mismatch')
    require(fw.image[SCALE_OFFSET:SCALE_OFFSET+4] == struct.pack('<f', 1.0), 'Unexpected baseline scale')
    return fw


def build(raw, scale):
    require(math.isfinite(scale) and scale in SCALES, 'Scale is outside the documented experiment list')
    fw = official(raw)
    image = bytearray(fw.image)
    image[SCALE_OFFSET:SCALE_OFFSET+4] = struct.pack('<f', scale)
    start, end = fw.crc_span
    image[start:end] = f'{zlib.crc32(image[:start]):08X}'.encode('ascii')
    streams, cursor = [], 0
    for old, stream in zip(fw.blocks, fw.streams):
        block = bytes(image[cursor:cursor+len(old)])
        cursor += len(old)
        if block != old:
            prop = stream[0]
            lc, rest = prop % 9, prop // 9
            lp, pb = rest % 5, rest // 5
            stream = lzma.compress(block, format=lzma.FORMAT_ALONE,
                                   filters=[dict(id=lzma.FILTER_LZMA1, dict_size=u32(stream, 1), lc=lc, lp=lp, pb=pb)])
        streams.append(stream)
    payload = b'\xff'*4+b''.join(struct.pack('>I', len(s))+s for s in streams)+fw.trailer
    header = bytearray(raw[:512])
    struct.pack_into('<I', header, 4, len(payload))
    struct.pack_into('<I', header, 8, zlib.crc32(payload))
    struct.pack_into('<I', header, 0x24, zlib.crc32(image))
    values = crc_values(payload)
    require(len(values) == struct.unpack_from('<H', header, 0x2e)[0], 'Unexpected CRC-table growth')
    struct.pack_into(f'<{len(values)}I', header, 0x30, *values)
    result = bytes(header)+payload
    audit(raw, result, scale)
    if scale == 1.0:
        require(result == raw, 'Neutral rebuild is not byte-identical')
    return result


def byte_ranges(old, new):
    require(len(old) == len(new), 'Cannot compare unequal layouts')
    ranges = []
    for offset, (a, b) in enumerate(zip(old, new)):
        if a == b:
            continue
        if ranges and offset == ranges[-1][1]:
            ranges[-1][1] += 1
        else:
            ranges.append([offset, offset+1])
    return [dict(start=hex(a), end_exclusive=hex(b), old_hex=old[a:b].hex(), new_hex=new[a:b].hex()) for a, b in ranges]


def audit(raw, candidate, scale):
    require(math.isfinite(scale) and scale in SCALES, 'Unsupported expected scale')
    a, b = official(raw), parse(candidate)
    require(len(a.image) == len(b.image) and a.crc_span == b.crc_span, 'Image layout changed')
    require(b.image[SCALE_OFFSET:SCALE_OFFSET+4] == struct.pack('<f', scale), 'Candidate scale differs from requested scale')
    allowed = set(range(SCALE_OFFSET, SCALE_OFFSET+4)) | set(range(*a.crc_span))
    actual = {i for i, (x, y) in enumerate(zip(a.image, b.image)) if x != y}
    require(actual <= allowed, 'Unexpected image changes outside scale/CRC')
    count = struct.unpack_from('<H', raw, 0x2e)[0]
    header_allowed = set(range(4, 12)) | set(range(0x24, 0x28)) | set(range(0x30, 0x30+4*count))
    header_actual = {i for i in range(512) if raw[i] != candidate[i]}
    require(header_actual <= header_allowed, 'Unexpected header identity/version/destination change')
    require(len(a.streams) == len(b.streams) == 10, 'Stream count changed')
    changed = [i for i, (x, y) in enumerate(zip(a.streams, b.streams)) if x != y]
    require(changed == ([] if scale == 1.0 else [9]), 'Unexpected compressed blocks changed')
    require(a.streams[9][:13] == b.streams[9][:13], 'LZMA properties or declared block size changed')
    require(a.trailer == b.trailer, 'Outer trailer changed; its numeric semantics are unresolved')
    return dict(source_sha256=sha(raw), candidate=b.summary(), scale=scale,
                image_changed_bytes=len(actual), image_changes=byte_ranges(a.image, b.image),
                header_changes=byte_ranges(raw[:512], candidate[:512]),
                only_scale_and_required_container_fields_changed=True,
                changed_compressed_blocks_zero_based=changed,
                device_boot='not tested by this tool', acoustic_performance='not measured')
