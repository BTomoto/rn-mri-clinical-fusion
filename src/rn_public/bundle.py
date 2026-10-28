"""Restore byte-identical source files from small GitHub-friendly ZIP parts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def restore_sources(root: Path) -> dict:
    root = root.resolve()
    manifest_path = root/'data/packed/source_bundle.json'
    if not manifest_path.exists():
        return {'restored_files': 0, 'status': 'no_bundle_manifest'}
    manifest = json.loads(manifest_path.read_text())
    missing = []
    for item in manifest['members']:
        path = root/item['path']
        if not path.is_file() or path.stat().st_size != item['size_bytes'] or sha256(path) != item['sha256']:
            missing.append(item)
    if not missing:
        return {'restored_files': 0, 'status': 'all_source_checksums_verified'}
    with tempfile.TemporaryFile(dir=manifest_path.parent) as stream:
        combined = hashlib.sha256()
        for item in manifest['parts']:
            path = root/item['path']
            if not path.is_file() or path.stat().st_size != item['size_bytes'] or sha256(path) != item['sha256']:
                raise ValueError(f'Missing or corrupt source-bundle part: {item["path"]}')
            with path.open('rb') as part:
                for block in iter(lambda: part.read(1024*1024), b''):
                    stream.write(block); combined.update(block)
        if combined.hexdigest() != manifest['archive_sha256']:
            raise ValueError('Combined source archive SHA256 mismatch')
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            if set(archive.namelist()) != {item['path'] for item in manifest['members']}:
                raise ValueError('Unexpected source archive members')
            for item in missing:
                path = (root/item['path']).resolve()
                if root not in path.parents:
                    raise ValueError('Unsafe source member path')
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_name(path.name+'.restore-partial')
                try:
                    digest = hashlib.sha256()
                    with archive.open(item['path']) as source, temporary.open('wb') as target:
                        for block in iter(lambda: source.read(1024*1024), b''):
                            target.write(block); digest.update(block)
                    if temporary.stat().st_size != item['size_bytes'] or digest.hexdigest() != item['sha256']:
                        raise ValueError(f'Restored source SHA256 mismatch: {item["path"]}')
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
    return {'restored_files': len(missing), 'status': 'restored_and_checksums_verified'}
