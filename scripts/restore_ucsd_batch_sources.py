"""Restore verified additional images from the Stage17 source ZIP, without path guessing."""
from pathlib import Path
import argparse,hashlib,json,zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('--output-root',type=Path);a=p.parse_args()
 receipt=json.loads((ROOT/'reports/ucsd_batch_features/source_archive_receipt.json').read_text())
 if a.archive.stat().st_size!=receipt['archive_bytes'] or digest(a.archive)!=receipt['archive_sha256']:raise ValueError('Source ZIP size/hash mismatch')
 manifest=ROOT/'reports/ucsd_batch_features/source_manifest.csv'
 if digest(manifest)!=receipt['source_manifest_sha256']:raise ValueError('Local source manifest changed')
 m=pd.read_csv(manifest);m=m[m.storage.eq('batch_package')]
 dest=a.output_root or ROOT.parent/'ucsd_batch_sources';dest.mkdir(parents=True,exist_ok=True)
 if dest.is_symlink():raise ValueError('Output directory must not be a symlink')
 restored=0;reused=0
 with zipfile.ZipFile(a.archive) as z:
  expected={'README.txt','source_manifest.csv'}|{'files/'+n for n in m.mirror_filename}
  if len(z.namelist())!=len(expected) or set(z.namelist())!=expected:raise ValueError('Unexpected archive members')
  for r in m.itertuples():
   name='files/'+r.mirror_filename;q=dest/r.mirror_filename
   if '/' in r.mirror_filename or '\\' in r.mirror_filename or q.is_symlink():raise ValueError('Invalid target member path')
   if q.exists() and q.stat().st_size==r.bytes and digest(q)==r.sha256:reused+=1;continue
   info=z.getinfo(name)
   if info.file_size!=r.bytes:raise ValueError('Member size mismatch')
   part=q.with_name(q.name+'.partial');h=hashlib.sha256();size=0
   try:
    with z.open(name) as src,part.open('wb') as target:
     for block in iter(lambda:src.read(1024**2),b''):
      size+=len(block)
      if size>r.bytes:raise ValueError('Member exceeds declared bytes')
      h.update(block);target.write(block)
    if size!=r.bytes or h.hexdigest()!=r.sha256:raise ValueError('Member hash mismatch')
    part.replace(q);restored+=1
   finally:part.unlink(missing_ok=True)
 print(json.dumps(dict(restored=restored,reused=reused,verified=restored+reused),indent=2))

if __name__=='__main__':main()
