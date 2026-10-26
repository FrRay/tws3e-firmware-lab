"""Portable CLI: inspect/unpack/build/verify. No device-write operation."""
import argparse
import json
import lzma
from pathlib import Path
import sys
import subprocess
from tws3e.core import SCALES, build, official, parse, require, sha


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect', help='Read format and checksums; does not edit')
    inspect.add_argument('input', type=Path)
    unpack = commands.add_parser('unpack', help='Extract the identified official image for research')
    unpack.add_argument('input', type=Path)
    unpack.add_argument('--output', type=Path, required=True)
    for name in ('build', 'verify'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--original', type=Path, required=True)
        cmd.add_argument('--scale', type=float, choices=SCALES, required=True)
        cmd.add_argument('--sevenzip', default='7z')
        if name == 'build':
            cmd.add_argument('--output', type=Path, required=True)
        else:
            cmd.add_argument('--candidate', type=Path, required=True)
            cmd.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inspect':
        result = parse(args.input.read_bytes()).summary()
    elif args.command == 'unpack':
        fw = official(args.input.read_bytes())
        require(not args.output.exists(), 'Output directory already exists; choose a fresh directory')
        args.output.mkdir(parents=True)
        (args.output/'image.bin').write_bytes(fw.image)
        (args.output/'header.bin').write_bytes(fw.raw[:512])
        save_json(args.output/'summary.json', fw.summary())
        result = fw.summary()
    else:
        from tws3e.verification import cross_check
        raw = args.original.read_bytes()
        data = build(raw, args.scale) if args.command == 'build' else args.candidate.read_bytes()
        report_path = args.output.with_suffix('.verification.json') if args.command == 'build' else args.report
        require(not report_path.exists(), 'Report already exists; use a fresh output path')
        if args.command == 'build':
            require(not args.output.exists(), 'Firmware already exists; use a fresh output path')
            require(args.output.resolve() != args.original.resolve(), 'Cannot overwrite original')
        else:
            require(report_path.resolve() not in (args.original.resolve(), args.candidate.resolve()), 'Report would overwrite an input')
        report = cross_check(raw, data, args.scale, args.sevenzip)
        if args.command == 'build':
            args.output.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation also protects against accidental reruns.
            with args.output.open('xb') as output:
                output.write(data)
            require(sha(args.output.read_bytes()) == sha(data), 'Written-file hash mismatch')
        save_json(report_path, report)
        result = dict(sha256=sha(data), bytes=len(data), scale=args.scale,
                      report=str(report_path), checks_complete=True,
                      note='Offline checks passed; acoustic stability and recovery are not established.')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, AssertionError, ImportError, lzma.LZMAError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
