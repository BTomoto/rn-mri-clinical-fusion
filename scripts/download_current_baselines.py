"""Get baseline studies added by clinical-version reconciliation, CRC/SHA checked."""
from pathlib import Path
import collections
import hashlib
import json
import sys
import zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.remotezip import parse_directory,download_members


def main():
    a=pd.read_csv(ROOT/'data/processed/followup_availability_current.csv',dtype={'patient_id':str,'baseline_study_date_code':str})
    needed=set(zip(a.loc[(a.baseline_directory_candidate==1)&(a.previous_archive_dicom_files==0),'patient_id'],
                   a.loc[(a.baseline_directory_candidate==1)&(a.previous_archive_dicom_files==0),'baseline_study_date_code']))
    destination=ROOT/'data/imaging/current_baseline_addition';selected=[]
    for archive in json.loads((ROOT/'data/metadata/archive_sources.json').read_text()):
        entries=[]
        for e in parse_directory((ROOT/archive['directory_path']).read_bytes()):
            parts=e['name'].split('/')
            if len(parts)<4 or not parts[0].isdigit() or not e['name'].lower().endswith('.dcm'):continue
            if (str(int(parts[0])),parts[1]) in needed:
                e.update(archive_id=archive['archive_id'],patient_id=str(int(parts[0])),study_date_code=parts[1]);entries.append(e)
        if entries:
            print(archive['archive_id'],len(entries),flush=True)
            print(download_members(archive['download_url'],entries,destination,workers=6),flush=True)
            selected.extend(entries)
    records=[]
    for e in selected:
        p=destination/e['name'];b=p.read_bytes()
        records.append(dict(member=e['name'],path=str(p.relative_to(ROOT)),archive_id=e['archive_id'],
            patient_id=e['patient_id'],study_date_code=e['study_date_code'],size_bytes=len(b),
            sha256=hashlib.sha256(b).hexdigest(),zip_crc32=e['crc32']))
    meta=ROOT/'data/metadata/endpoint_followup'
    with (meta/'additional_baseline_imaging.jsonl').open('w') as f:
        for r in records:f.write(json.dumps(r)+'\n')
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    output=dist/'RN_MRI_Baseline_Addition_20261028.zip'
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for r in records:z.write(ROOT/r['path'],arcname='data/imaging/dicom/'+r['member'])
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    summary=dict(archive_name=output.name,archive_size_bytes=output.stat().st_size,archive_sha256=digest,
        studies=len({(r['patient_id'],r['study_date_code']) for r in records}),dicom_files=len(records),
        uncompressed_bytes=sum(r['size_bytes'] for r in records),
        source_studies=[dict(patient_id=p,study_date_code=d) for p,d in sorted(needed)],
        integrity='ZIP member size and CRC32 verified; per-file SHA256 recorded',full_image_qc_complete=False)
    (ROOT/'reports/additional_baseline_imaging.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
