"""Restore complete series corresponding to current baseline masks, SHA verified.

Uses existing 16 archive parts or --download-missing to obtain the same official
Figshare members. No filenames, masks, time points or clinical fields are changed.
"""
from pathlib import Path
import argparse
import hashlib
import gzip
import json
import sys
import zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.remotezip import download_members,parse_directory
from rn_public.imaging_qc import resolve_series_name


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-missing',action='store_true')
    args=parser.parse_args()
    a=pd.read_csv(ROOT/'data/processed/followup_availability_current.csv',dtype={'patient_id':str,'baseline_mask_date_code':str})
    a=a[a.baseline_mask_available==1]
    original={e['path'].removeprefix('data/imaging/dicom/'):e for e in map(json.loads,(ROOT/'data/metadata/downloaded_imaging.jsonl').read_text().splitlines())}
    sources={e['name']:e for e in map(json.loads,(ROOT/'data/metadata/selected_dicom_members.jsonl').read_text().splitlines())}
    added=[json.loads(x) for x in (ROOT/'data/metadata/endpoint_followup/additional_baseline_imaging.jsonl').read_text().splitlines()]
    targets=set();mapping=[]
    for r in a.itertuples():
        name=str(r.baseline_mask_file).removeprefix(f'{r.patient_id}_{r.baseline_mask_date_code}_').removesuffix('_msk.nii')
        available={e['series_name'] for e in sources.values() if e['patient_id']==r.patient_id and e['study_date_code']==r.baseline_mask_date_code}
        available.update(Path(e['member']).parent.name for e in added if e['patient_id']==r.patient_id and e['study_date_code']==r.baseline_mask_date_code)
        resolved,rule=resolve_series_name(name,available)
        targets.add((r.patient_id,r.baseline_mask_date_code,resolved))
        mapping.append(dict(lesion_key=r.lesion_key,patient_id=r.patient_id,study_date_code=r.baseline_mask_date_code,
                            mask_series_name=name,dicom_series_name=resolved,name_match_rule=rule))
    selected=[]
    for name,e in original.items():
        source=sources[name]
        if (source['patient_id'],source['study_date_code'],source['series_name']) in targets:
            selected.append(dict(e,member=name))
    for e in added:
        if (e['patient_id'],e['study_date_code'],Path(e['member']).parent.name) in targets:selected.append(e)
    if len({e['member'] for e in selected})!=len(selected):raise ValueError('Duplicate source members')
    represented={(e['patient_id'],e['study_date_code'],Path(e['member']).parent.name) for e in selected}
    if represented!=targets:raise ValueError(f'Missing source series {targets-represented}')
    wanted={e['member']:e for e in selected};restored=0;verified_parts=[]
    for part in json.loads((ROOT/'data/metadata/imaging_archive_parts.json').read_text()):
        path=ROOT/'dist/restored_mri'/part['filename']
        if not path.is_file():path=ROOT/part['relative_path']
        if not path.is_file():continue
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=part['sha256']:raise ValueError(f'Archive SHA mismatch: {part["filename"]}')
        verified_parts.append(dict(filename=part['filename'],sha256=digest))
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                member=info.filename.removeprefix('data/imaging/dicom/')
                if member not in wanted:continue
                e=wanted[member];raw=z.read(info)
                if hashlib.sha256(raw).hexdigest()!=e['sha256']:raise ValueError(f'Source SHA mismatch: {member}')
                p=ROOT/'data/imaging/dicom'/member;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);restored+=1
    for e in selected:
        member=e['member'];p=ROOT/'data/imaging/dicom'/member
        addition=ROOT/e['path']
        if not p.is_file() and addition.is_file():p=addition
        e['path']=str(p.relative_to(ROOT))
    missing=[e for e in selected if not (ROOT/e['path']).is_file()]
    if missing and args.download_missing:
        for archive in json.loads((ROOT/'data/metadata/archive_sources.json').read_text()):
            needed={e['member'] for e in missing if e['archive_id']==archive['archive_id']}
            candidates=sources
            if any(name not in sources for name in needed):
                candidates={**sources,**{e['name']:e for e in parse_directory((ROOT/archive['directory_path']).read_bytes())}}
            entries=[candidates[name] for name in needed]
            if entries:download_members(archive['download_url'],entries,ROOT/'data/imaging/dicom')
    for e in selected:
        p=ROOT/e['path']
        if not p.is_file():raise FileNotFoundError(f'Restore archived MRI or use --download-missing: {e["member"]}')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:raise ValueError(f'Final SHA mismatch: {e["member"]}')
    out=ROOT/'data/metadata/baseline_qc';out.mkdir(exist_ok=True)
    (out/'mask_series_members.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in sorted(selected,key=lambda x:x['member'])))
    (out/'mask_series_members.jsonl.gz').write_bytes(gzip.compress((out/'mask_series_members.jsonl').read_bytes(),mtime=0))
    pd.DataFrame(mapping).to_csv(out/'series_name_mapping.csv',index=False)
    summary=dict(scope='complete series named by current baseline masks',lesions=len(a),patients=int(a.patient_id.nunique()),
                 studies=len({(p,d) for p,d,n in targets}),series_directories=len(targets),dicom_files=len(selected),
                 bytes=sum(e['size_bytes'] for e in selected),restored_from_parts=restored,verified_archive_parts=verified_parts,
                 all_selected_file_sha256_match=True,all_project_selected_mri_restored=False)
    (ROOT/'reports/baseline_series_restoration.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
