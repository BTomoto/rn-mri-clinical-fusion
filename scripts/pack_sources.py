"""Preserve large tabular/index source files in reversible 2 MiB archive parts."""
import json
from pathlib import Path
import subprocess
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rn_public.bundle import sha256

root=Path(__file__).resolve().parents[1]
out=root/'data/packed'
out.mkdir(parents=True,exist_ok=True)
manifest_path=out/'source_bundle.json'
if manifest_path.exists():
    files=[item['path'] for item in json.loads(manifest_path.read_text())['members']]
else:
    files=[p for p in subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
           if (root/p).is_file() and (root/p).stat().st_size>3*1024*1024]
if not files or not all((root/name).is_file() for name in files):
    raise ValueError('Restore the full source files before building their archive')
combined=out/'research_sources.zip'
with zipfile.ZipFile(combined,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name in files:
        archive.write(root/name,arcname=name)
manifest={'format':'ordered_binary_segments_of_one_zip','archive_sha256':sha256(combined),
          'archive_size_bytes':combined.stat().st_size,
          'members':[{'path':name,'size_bytes':(root/name).stat().st_size,'sha256':sha256(root/name)} for name in files],
          'parts':[]}
with combined.open('rb') as source:
    index=0
    while block:=source.read(2*1024*1024):
        index+=1
        p=out/f'research_sources.zip.part-{index:04d}'
        p.write_bytes(block)
        manifest['parts'].append({'path':str(p.relative_to(root)),'size_bytes':p.stat().st_size,'sha256':sha256(p)})
(out/'source_bundle.json').write_text(json.dumps(manifest,indent=2))
combined.unlink()
print('Packed',len(files),'source files into',len(manifest['parts']),'parts;',manifest['archive_size_bytes'],'bytes')
