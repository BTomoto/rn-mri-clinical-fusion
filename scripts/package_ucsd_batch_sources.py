"""Archive only additional large source images; six-case Git samples stay in Git."""
from pathlib import Path
import argparse,json,hashlib,zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-root',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 batch=a.input_root or ROOT.parent/'ucsd_batch_sources'
 output=a.output or ROOT.parent/'batch_source_deliverable/UCSD_MRI_Batch_Additional_Sources_20261029.zip'
 manifest=ROOT/'reports/ucsd_batch_features/source_manifest.csv';d=pd.read_csv(manifest);additional=d[d.storage.eq('batch_package')]
 if len(d)!=546 or len(additional)!=528:raise ValueError('Unexpected fixed batch manifest')
 for r in additional.itertuples():
  q=batch/r.mirror_filename
  if not q.is_file() or q.is_symlink() or q.stat().st_size!=r.bytes or digest(q)!=r.sha256:raise ValueError('Missing/corrupt batch source: '+r.mirror_filename)
 output.parent.mkdir(parents=True,exist_ok=True);part=output.with_name(output.name+'.partial')
 def member(name,data):
  info=zipfile.ZipInfo(name,date_time=(2026,10,29,0,0,0));info.compress_type=zipfile.ZIP_STORED;info.create_system=3;info.external_attr=0o100644<<16
  archive.writestr(info,data)
 with zipfile.ZipFile(part,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
  member('source_manifest.csv',manifest.read_bytes())
  member('README.txt',('Additional UCSD-PTGBM mirror source images for Stage17.\n'
    'Contains 528 source NIfTI files not already stored among the six-case Git samples.\n'
    'The 18 remaining required files are in data/samples/ucsd_mirror/ in the GitHub repository.\n'
    'Restore from the project root: python scripts/restore_ucsd_batch_sources.py /path/to/this.zip\n'
    'No source bytes, native coordinates or intensity scaling were changed.\n'
    'Unknown spatial units and uint8 intensity limits remain; no original quantitative ADC is supplied.\n'
    'Data: UCSD-PTGBM DOI 10.7937/fwv2-dt74; descriptor DOI 10.1038/s41597-025-06499-z.\n'
    'Original data CC BY 4.0; mirror curator https://github.com/data-nih/tcia .\n').encode())
  for r in additional.sort_values('mirror_filename').itertuples():member('files/'+r.mirror_filename,(batch/r.mirror_filename).read_bytes())
 part.replace(output)
 receipt=dict(filename=output.name,archive_bytes=output.stat().st_size,archive_sha256=digest(output),
              additional_source_files=len(additional),additional_source_bytes=int(additional.bytes.sum()),
              existing_Git_sample_files=18,total_required_files=546,format='ZIP_STORED',
              source_manifest_sha256=digest(manifest),source_images_modified=False,
              batch_source_archive_in_Git=False,repository_contains_features_code_and_manifests=True)
 (ROOT/'reports/ucsd_batch_features/source_archive_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
