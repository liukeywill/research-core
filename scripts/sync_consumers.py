#!/usr/bin/env python3
"""Vendor committed research rules; never fetch, commit, or alter project state."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

SOURCE = Path(__file__).resolve().parent.parent
ORIGIN = 'https://github.com/liukeywill/research-core'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def member(root, relative):
    part = Path(relative)
    if part.is_absolute() or '..' in part.parts or not part.parts:
        raise ValueError('Unsafe module path: ' + relative)
    path = root / part
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Unsafe module file: ' + relative)
    return path


def load_source(source=SOURCE):
    source = Path(source)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Expected a committed Git source')
    manifest = json.loads((source / 'module.json').read_text(encoding='utf-8'))
    if manifest.get('name') != 'research-core' or not manifest.get('version') or not manifest.get('files'):
        raise ValueError('Invalid module manifest')
    payload = {'module.json': (source / 'module.json').read_bytes()}
    for relative, expected in manifest['files'].items():
        data = member(source, relative).read_bytes()
        if digest(data) != expected:
            raise ValueError('Source hash mismatch: ' + relative)
        payload[relative] = data
    for relative, data in payload.items():
        committed = subprocess.check_output(['git', 'show', revision + ':' + relative], cwd=source)
        if committed != data:
            raise ValueError('Commit source changes before syncing: ' + relative)
    lock = {'name': 'research-core', 'version': manifest['version'], 'source': ORIGIN,
            'source_commit': revision, 'files': {p: digest(data) for p, data in payload.items()}}
    return payload, lock


def inspect_target(target):
    target = Path(target).resolve()
    if not (target / 'SKILL.md').is_file():
        raise ValueError('Target must be a Skill directory: ' + str(target))
    shared = target / 'shared'
    if shared.is_symlink():
        raise ValueError('Refusing symlinked shared directory')
    vendor, lock_path = shared / 'research-core', shared / 'research-core.lock.json'
    if vendor.is_symlink() or lock_path.is_symlink():
        raise ValueError('Refusing symlinked module or lock')
    if not vendor.exists() and not lock_path.exists():
        return target, vendor, lock_path, {}
    if not vendor.is_dir() or not lock_path.is_file():
        raise ValueError('Incomplete module installation: ' + str(target))
    old = json.loads(lock_path.read_text(encoding='utf-8'))
    if old.get('name') != 'research-core' or not isinstance(old.get('files'), dict):
        raise ValueError('Invalid existing lock: ' + str(target))
    actual = {p.relative_to(vendor).as_posix() for p in vendor.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != set(old['files']):
        raise ValueError('Untracked or missing vendored files: ' + str(target))
    for relative, expected in old['files'].items():
        if digest(member(vendor, relative).read_bytes()) != expected:
            raise ValueError('Consumer has local module edits: ' + str(target / relative))
    return target, vendor, lock_path, old


def sync(target, payload, lock, check=False):
    target, vendor, lock_path, old = inspect_target(target)
    if check:
        if old != lock:
            raise ValueError('Consumer version or source differs: ' + str(target))
        for relative, data in payload.items():
            if member(vendor, relative).read_bytes() != data:
                raise ValueError('Consumer differs: ' + relative)
        return
    vendor.mkdir(parents=True, exist_ok=True)
    for relative in set(old.get('files', {})) - set(payload):
        member(vendor, relative).unlink()
    for relative, data in payload.items():
        path = member(vendor, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', action='append', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        payload, lock = load_source()
        # Preflight all consumers before changing any of them.
        for target in args.target:
            inspect_target(target)
        for target in args.target:
            sync(target, payload, lock, args.check)
            print(('Verified ' if args.check else 'Synced ') + str(target) + ' @ ' + lock['source_commit'])
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
