"""Read-only public Aspera folder/file inventory for the 59-timepoint released test package.

This is a metadata inventory, not a NIfTI download or a quality pass.
"""
from pathlib import Path
import argparse,base64,datetime as dt,json,re,urllib.parse
import pandas as pd
from audit_ucsd_mri_access import request,Links,public_token,PAGE,HOST
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/ucsd_feature_audit'


def refresh(token_file=None):
    if token_file:
        token=json.loads(Path(token_file).read_text())['access_token']
    else:
        _,page=request(PAGE);p=Links();p.feed(page.decode(errors='replace'))
        contexts=[json.loads(base64.b64decode(urllib.parse.parse_qs(urllib.parse.urlsplit(u).query)['context'][0])) for u in p.links]
        c=next(c for c in contexts if c['package_id']=='1221')
        _,b=request(HOST+'/aspera/faspex/config.js');cfg=b.decode()
        client=re.search(r"client_id:\s*'([^']+)'",cfg).group(1)
        redirect=HOST+re.search(r"redirect_uri:\s*'([^']+)'",cfg).group(1)
        token=public_token(c,client,redirect,{})
    path='/UCSD-PTGBM-BraTS-2024-test-set'
    endpoint=HOST+'/aspera/faspex/api/v5/packages/1221/files/received?limit=1000'
    headers={'Authorization':'Bearer '+token}
    r,b=request(endpoint,dict(path=path,sort='path'),headers);j=json.loads(b)
    if len(j['items']) != j['total_count']:
        raise ValueError('Incomplete folder inventory; pagination required')
    folders=pd.DataFrame([{k:x.get(k) for k in ['path','basename','type','size']} for x in j['items']])
    if not folders.basename.str.fullmatch(r'UCSD-PTGBM-\d{4}_\d{2}').all():
        raise ValueError('New folder naming requires review')
    cases=pd.read_csv(ROOT/'data/processed/ucsd_clinical_baseline_cohort.csv')
    inventory=folders.rename(columns={'basename':'ID'}).merge(cases[['ID','patient_id','tumor_label','negative_list_dx']],on='ID',how='left',validate='one_to_one',indicator=True)
    if not inventory._merge.eq('both').all():raise ValueError('Unmatched clinical ID in MRI folder inventory')
    inventory.drop(columns='_merge').to_csv(OUT/'mri_folder_inventory_1221.csv',index=False)
    rec=dict(package_id='1221',date='2026-10-29',checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
             endpoint=endpoint,folders_http_status=r.status,folders=len(inventory),
             patients=int(inventory.patient_id.nunique()),tumor_timepoints=int(inventory.tumor_label.sum()),
             treatment_change_timepoints=int(inventory.tumor_label.eq(0).sum()),
             folder_clinical_ID_match=True,folder_name_matches_do_not_adjudicate_BraTS_conflict=True,
             imaging_files_downloaded=0,pixel_quality_review_complete=False,samples=[])
    print('Listed',len(inventory),'case folders, matched',rec['patients'],'source patients',flush=True)
    files=[]
    for ID in ['UCSD-PTGBM-0001_01','UCSD-PTGBM-0003_01']:
        p=inventory.set_index('ID').at[ID,'path']
        probe=dict(ID=ID,request_path=p)
        try:
            r,b=request(endpoint,dict(path=p,sort='path'),headers);j=json.loads(b)
            if len(j['items'])!=j['total_count']:raise ValueError('Partial file list')
            subset=[dict(ID=ID,**{k:x.get(k) for k in ['path','basename','type','size']}) for x in j['items']]
            files.extend(subset);probe.update(http_status=r.status,success=True,listed_files=len(subset))
        except Exception as e:probe.update(success=False,error=type(e).__name__)
        rec['samples'].append(probe);print(ID,probe,flush=True)
    pd.DataFrame(files).to_csv(OUT/'mri_sample_file_inventory.csv',index=False)
    (OUT/'mri_inventory_receipt.json').write_text(json.dumps(rec,indent=2))
    return rec


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');p.add_argument('--session-token-file');a=p.parse_args()
    if a.session_token_file and not a.refresh:p.error('--session-token-file requires --refresh')
    r=refresh(a.session_token_file) if a.refresh else json.loads((OUT/'mri_inventory_receipt.json').read_text())
    print(json.dumps(r,indent=2))
