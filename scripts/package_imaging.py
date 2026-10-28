"""Create independent ZIP parts for durable storage and GitHub Release assets."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
destination = root / 'dist'
destination.mkdir(exist_ok=True)
downloaded = [json.loads(line) for line in (root/'data/metadata/downloaded_imaging.jsonl').open()]
selected = {r['name']: r for r in (json.loads(line) for line in (root/'data/metadata/selected_dicom_members.jsonl').open())}
chunks = []
current = []
estimated = 0
for record in downloaded:
    name = record['path'].removeprefix('data/imaging/dicom/')
    size = selected[name]['compressed_size']
    if current and estimated + size > 360*1024*1024:
        chunks.append(current); current=[]; estimated=0
    current.append(record); estimated += size
if current:
    chunks.append(current)


def package(item):
    index, rows = item
    path = destination / f'RN_MRI_part_{index:02d}_of_{len(chunks):02d}.zip'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for record in rows:
            archive.write(root / record['path'], arcname=record['path'])
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist()
        assert len(infos)==len(rows)
        for info, record in zip(infos, rows):
            assert info.filename==record['path'] and info.file_size==record['size_bytes']
            assert info.CRC==record['zip_crc32']
    if path.stat().st_size >= 480*1024*1024:
        raise ValueError(f'Part too large for planned transfer: {path.name}')
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    result=dict(filename=path.name, relative_path=str(path.relative_to(root)),
                size_bytes=path.stat().st_size, sha256=digest.hexdigest(),
                dicom_files=len(rows), uncompressed_bytes=sum(r['size_bytes'] for r in rows))
    print(json.dumps(result), flush=True)
    return result


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    parts=list(executor.map(package, enumerate(chunks,1)))
assert sum(p['dicom_files'] for p in parts)==len(downloaded)
(root/'data/metadata/imaging_archive_parts.json').write_text(json.dumps(parts,indent=2))
print('PACKAGING COMPLETE',len(parts),'parts',sum(p['size_bytes'] for p in parts),'bytes',flush=True)
