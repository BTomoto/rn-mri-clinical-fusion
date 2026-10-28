"""Recover all named non-T1 FLAIR candidates in the 48 baseline mask studies."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import sys
import zipfile
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.remotezip import download_members


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-missing',action='store_true');args=parser.parse_args()
    masks=pd.read_csv(ROOT/'data/processed/cohort_baseline_mask_alignment.csv',dtype={'patient_id':str,'study_date_code':str})
    studies=set(zip(masks.patient_id,masks.study_date_code))
    prior={e['path'].removeprefix('data/imaging/dicom/'):e for e in map(json.loads,(ROOT/'data/metadata/downloaded_imaging.jsonl').read_text().splitlines())}
    sources={e['name']:e for e in map(json.loads,(ROOT/'data/metadata/selected_dicom_members.jsonl').read_text().splitlines())}
    added=[json.loads(x) for x in (ROOT/'data/metadata/endpoint_followup/additional_baseline_imaging.jsonl').read_text().splitlines()]
    selected=[]
    for name,e in prior.items():
        src=sources[name];sn=src['series_name'].upper()
        if (e['patient_id'],e['study_date_code']) in studies and 'FLAIR' in sn and 'T1' not in sn:selected.append(dict(e,member=name))
    for e in added:
        sn=Path(e['member']).parent.name.upper()
        if (e['patient_id'],e['study_date_code']) in studies and 'FLAIR' in sn and 'T1' not in sn:selected.append(e)
    wanted={e['member']:e for e in selected}
    if len(wanted)!=len(selected):raise ValueError('Duplicate FLAIR members')
    verified=[]
    for part in json.loads((ROOT/'data/metadata/imaging_archive_parts.json').read_text()):
        p=ROOT/'dist/restored_mri'/part['filename']
        if not p.is_file():p=ROOT/part['relative_path']
        if not p.is_file():continue
        with p.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=part['sha256']:raise ValueError('Archive SHA mismatch')
        verified.append(part['filename'])
        with zipfile.ZipFile(p) as z:
            for info in z.infolist():
                name=info.filename.removeprefix('data/imaging/dicom/')
                if name not in wanted:continue
                raw=z.read(info)
                if hashlib.sha256(raw).hexdigest()!=wanted[name]['sha256']:raise ValueError('FLAIR source SHA mismatch')
                target=ROOT/'data/imaging/dicom'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    for e in selected:
        p=ROOT/'data/imaging/dicom'/e['member']
        if not p.is_file() and (ROOT/e['path']).is_file():p=ROOT/e['path']
        e['path']=str(p.relative_to(ROOT))
    missing=[e for e in selected if not (ROOT/e['path']).is_file()]
    if missing and args.download_missing:
        from rn_public.remotezip import parse_directory
        for archive in json.loads((ROOT/'data/metadata/archive_sources.json').read_text()):
            needed={e['member'] for e in missing if e['archive_id']==archive['archive_id']}
            if not needed:continue
            lookup={e['name']:e for e in parse_directory((ROOT/archive['directory_path']).read_bytes())}
            download_members(archive['download_url'],[lookup[name] for name in needed],ROOT/'data/imaging/dicom')
    for e in selected:
        p=ROOT/e['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:raise ValueError(f'Restore required FLAIR member: {e["member"]}')
    out=ROOT/'data/metadata/baseline_qc'
    raw=''.join(json.dumps(e)+'\n' for e in sorted(selected,key=lambda x:x['member'])).encode()
    (out/'flair_series_members.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    covered={(e['patient_id'],e['study_date_code']) for e in selected}
    summary=dict(dicom_files=len(selected),series_directories=len({str(Path(e['member']).parent) for e in selected}),
        studies_with_named_flair=len(covered),studies_without_named_flair=len(studies-covered),
        source_bytes=sum(e['size_bytes'] for e in selected),manifest_sha256=hashlib.sha256(raw).hexdigest(),
        all_selected_sha256_match=True,verified_archive_parts=verified,
        missing_studies=[dict(patient_id=p,study_date_code=d) for p,d in sorted(studies-covered)],
        selection='All directory names containing FLAIR but not T1 in the 48 baseline mask studies; sequence type not clinically adjudicated')
    (ROOT/'reports/flair_series_restoration.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
