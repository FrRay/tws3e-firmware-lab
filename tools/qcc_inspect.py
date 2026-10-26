"""List, compare and extract supplied QCC APPUHDR5 firmware records."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct

def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_records(data):
    offset, records = 0, []
    while offset < len(data):
        require(offset + 12 <= len(data), 'Truncated record header')
        kind = data[offset:offset + 8]
        require(kind in (b'APPUHDR5', b'PARTDATA', b'APPUPFTR'), f'Unknown record at {offset:x}')
        size = int.from_bytes(data[offset + 8:offset + 12], 'big')
        end = offset + 12 + size
        require(end <= len(data), 'Record exceeds file')
        payload = data[offset + 12:end]
        record = dict(kind=kind.decode(), offset=offset, bytes=size, sha256=sha(payload))
        if kind == b'PARTDATA':
            require(size >= 4, 'Missing partition ID')
            record.update(partition_id=int.from_bytes(payload[:4], 'big'), data=payload[4:])
        else:
            record['data'] = payload
        records.append(record)
        offset = end
    require(records[0]['kind'] == 'APPUHDR5' and records[-1]['kind'] == 'APPUPFTR', 'Bad container sequence')
    require(records[-1]['bytes'] == 256, 'Unexpected footer size')
    ids = [r['partition_id'] for r in records if 'partition_id' in r]
    require(len(ids) == len(set(ids)), 'Duplicate partition IDs')
    require(not any(r['kind'] != 'PARTDATA' for r in records[1:-1]), 'Unexpected nested record')
    return records


def parse_file_fs(data):
    require(data[:4] == b'File', 'Not a byte-oriented File filesystem')
    size, count = struct.unpack_from('<II', data, 4)
    require(size == len(data), 'Filesystem size mismatch')
    require(0 < count < 4096 and 12 + count * 12 <= size, 'Invalid filesystem table')
    entries = []
    for index in range(count):
        name_field, start, length = struct.unpack_from('<III', data, 12 + index * 12)
        is_directory = bool(name_field & 0x80000000)
        name_at = name_field & 0x7fffffff
        if name_at:
            require(name_at + 2 <= size, 'Filename outside filesystem')
            name_len = struct.unpack_from('<H', data, name_at)[0]
            require(name_len and name_at + 2 + name_len <= size, 'Invalid filename length')
            name = data[name_at + 2:name_at + 2 + name_len].decode('ascii')
        else:
            name = ''
        entry = dict(index=index, name=name, name_offset=name_at, directory=is_directory,
                     data_offset=start, bytes=length)
        if is_directory:
            require(1 <= start <= count and start - 1 + length <= count, 'Invalid child range')
        else:
            require(start + length <= size and start >= 12 + count * 12, 'File outside data area')
            entry['data'] = data[start:start + length]
            entry['sha256'] = sha(entry['data'])
        entries.append(entry)
    paths = {}
    seen = set()
    def walk(index, parent):
        require(index not in seen, 'Filesystem cycle or duplicate entry')
        seen.add(index)
        entry = entries[index]
        path = '/'.join(x for x in (parent, entry['name']) if x)
        if entry['directory']:
            for child in range(entry['data_offset'] - 1, entry['data_offset'] - 1 + entry['bytes']):
                walk(child, path)
        else:
            require(path not in paths, 'Duplicate file path')
            require(not any(x in ('.', '..') for x in path.split('/')), 'Unsafe file name')
            paths[path] = entry
    walk(0, '')
    require(len(seen) == count, 'Unreachable filesystem entry')
    # Every file interval is bounded and nonoverlapping; account for alignment gaps.
    regions = sorted((e['data_offset'], e['data_offset'] + e['bytes']) for e in paths.values())
    require(all(a[1] <= b[0] for a, b in zip(regions, regions[1:])), 'Overlapping file payloads')
    return paths


def inspect(path):
    raw = path.read_bytes()
    records = parse_records(raw)
    result = dict(file=path.name, bytes=len(raw), sha256=sha(raw),
                  header_hex=records[0]['data'].hex(), records=[], files={})
    for record in records:
        item = {key: value for key, value in record.items() if key != 'data'}
        payload = record['data']
        if 'partition_id' in record and payload.startswith(b'File'):
            files = parse_file_fs(payload)
            item['files'] = {name: dict(bytes=e['bytes'], sha256=e['sha256']) for name, e in files.items()}
            for name, metadata in item['files'].items():
                result['files'][str(record['partition_id'])+'/'+name] = metadata
        result['records'].append(item)
    return result, records


def extract(records, directory):
    require(not directory.exists(), 'Extraction directory already exists; choose a fresh path')
    directory.mkdir(parents=True)
    base = directory.resolve()
    for record in records:
        if 'partition_id' not in record:
            continue
        pid = record['partition_id']
        payload = record['data']
        (directory/f'partition_{pid:02d}.bin').write_bytes(payload)
        if not payload.startswith(b'File'):
            continue
        for name, entry in parse_file_fs(payload).items():
            relative = PurePosixPath(name.replace('\\', '/'))
            require(not relative.is_absolute() and all(part not in ('.', '..') and ':' not in part for part in relative.parts),
                    'Unsafe embedded filename')
            target = directory/f'partition_{pid:02d}_files'/Path(*relative.parts)
            require(target.resolve().is_relative_to(base), 'Embedded filename escapes extraction directory')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(entry['data'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--extract', type=Path)
    args = parser.parse_args()
    result, records = inspect(args.input)
    if args.compare:
        other, _ = inspect(args.compare)
        before, after = result['files'], other['files']
        old_parts = {r['partition_id']: r['sha256'] for r in result['records'] if 'partition_id' in r}
        new_parts = {r['partition_id']: r['sha256'] for r in other['records'] if 'partition_id' in r}
        result = dict(before=result['file'], after=other['file'],
                      source_sha256=result['sha256'], target_sha256=other['sha256'],
                      changed_partitions=[pid for pid in sorted(old_parts.keys() | new_parts.keys()) if old_parts.get(pid) != new_parts.get(pid)],
                      added_files=sorted(after.keys()-before.keys()),
                      removed_files=sorted(before.keys()-after.keys()),
                      changed_files=[name for name in sorted(before.keys() & after.keys()) if before[name] != after[name]])
    if args.extract:
        extract(records, args.extract)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
