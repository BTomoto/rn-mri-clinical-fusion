"""Audit the author-hosted bulk package without replacing analysis feature files."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,help='Existing copy of the pinned author Excel ZIP')
    args=parser.parse_args()
    inv=json.loads((ROOT/'data/metadata/endpoint_followup/molab_excel_archive_inventory.json').read_text())
    if args.archive:
        payload=args.archive.read_bytes()
    else:
        request=urllib.request.Request(inv['url'],headers={'User-Agent':'RNPublicDataAudit/1.0'})
        payload=urllib.request.urlopen(request,timeout=60).read()
    if hashlib.sha256(payload).hexdigest()!=inv['sha256']:raise ValueError('Author package SHA256 changed')
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        for entry in inv['files']:
            if hashlib.sha256(z.read(entry['name'])).hexdigest()!=entry['sha256']:
                raise ValueError('Archive member differs from provenance')
        radio=pd.read_excel(io.BytesIO(z.read('EXCEL FILES/OpenBTAI_RADIOMICS.xlsx')))
        morph=pd.read_excel(io.BytesIO(z.read('EXCEL FILES/OpenBTAI_MORPHOLOGICAL_MEASUREMENTS.xlsx')))
    current=radio[radio.Segment=='Total'].copy()
    old=pd.read_csv(ROOT/'data/processed/radiomics_existing_total.csv')
    def keys(d,p,t,l):
        return set(zip(d[p].astype(int),d[t].astype(int),d[l].astype(int)))
    k1=keys(current,'Patient','Timepoint','Lesion');k0=keys(old,'Patient','Timepoint','Lesion')
    report=dict(author_archive_url=inv['url'],author_archive_sha256=inv['sha256'],
        author_radiomics_rows=len(radio),author_radiomics_columns=len(radio.columns),
        author_radiomics_segment_counts=radio.Segment.value_counts().to_dict(),
        author_radiomics_patients=int(radio.Patient.nunique()),
        author_total_unique_lesions=len(set(zip(current.Patient,current.Lesion))),
        author_morphology_rows=int(morph.PATIENT.notna().sum()),
        author_morphology_year_counts=morph['TIME POINT'].dropna().astype(int).astype(str).str[:4].value_counts().sort_index().to_dict(),
        figshare_total_records=len(old),author_total_records=len(current),
        shared_patient_date_lesion_keys=len(k0&k1),figshare_only_keys=len(k0-k1),author_only_keys=len(k1-k0),
        action='retain_verified_figshare_features_with_explicit_version; do_not_silently_replace')
    (ROOT/'reports/molab_package_comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
