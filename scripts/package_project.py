"""Package the Git-ready project separately from its large MRI Release assets."""
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
out=root/'dist/RN_Research_Project.zip'
excluded={'dist','.git','__pycache__','.ipynb_checkpoints','node_modules'}
records=[]
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel=p.relative_to(root)
        if any(x in excluded for x in rel.parts) or rel.parts[:2]==('data','imaging'):
            continue
        if p.name.startswith('preview_') or p.name.endswith('.inspect.ndjson'):
            continue
        archive.write(p,arcname=str(Path(root.name)/rel))
        records.append(dict(path=str(rel),size_bytes=p.stat().st_size))
with zipfile.ZipFile(out) as archive:
    assert archive.testzip() is None
print(json.dumps(dict(path=str(out),files=len(records),size_bytes=out.stat().st_size,
                     sha256=hashlib.sha256(out.read_bytes()).hexdigest())))
