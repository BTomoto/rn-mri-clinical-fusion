"""Verify two archive-order samples per selected directory; not full image QC.

No model labels are assigned. All bytes come from the official Figshare ZIPs.
Run from any working directory. Downloads are resumable and CRC-checked.
"""
from pathlib import Path
import collections
import concurrent.futures
import hashlib
import json
import sys
import numpy as np
import pandas as pd
import pydicom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from rn_public.remotezip import download_members


def main():
    groups = collections.defaultdict(list)
    for line in (ROOT / 'data/metadata/selected_dicom_members.jsonl').read_text().splitlines():
        e = json.loads(line)
        groups[(e['patient_id'], e['study_date_code'], e['series_name'], e['archive_id'])].append(e)
    chosen = []
    for entries in groups.values():
        entries.sort(key=lambda e: e['offset'])
        chosen.extend({e['name']: e for e in [entries[0], entries[-1]]}.values())
    destination = ROOT / 'data/imaging/qa_samples'
    archives = json.loads((ROOT / 'data/metadata/archive_sources.json').read_text())
    def download_archive(a):
        entries = [e for e in chosen if e['archive_id'] == a['archive_id']]
        if entries:
            print(a['archive_id'], len(entries), flush=True)
            print(a['archive_id'], download_members(a['download_url'], entries, destination, workers=6), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(download_archive, archives))
    records = []
    original={}
    for line in (ROOT/'data/metadata/downloaded_imaging.jsonl').read_text().splitlines():
        e=json.loads(line)
        original[e['path'].removeprefix('data/imaging/dicom/')]=e['sha256']
    for key, entries in sorted(groups.items()):
        entries.sort(key=lambda e: e['offset'])
        sample_entries = list({e['name']: e for e in [entries[0], entries[-1]]}.values())
        r = dict(patient_id=key[0], study_date_code=key[1], series_name=key[2], archive_id=key[3],
                 directory_dicom_count=len(entries), sampled_files=len(sample_entries),
                 qc_scope='archive_order_samples_only', full_series_qc_complete=0)
        ds = []
        try:
            for e in sample_entries:
                p = destination / e['name']
                ds.append(pydicom.dcmread(p, stop_before_pixels=True))
            d = ds[0]
            def val(tag):
                x = getattr(d, tag, '')
                return '\\'.join(map(str, x)) if isinstance(x, (list, pydicom.multival.MultiValue)) else str(x)
            for tag in ['Modality','SeriesDescription','ProtocolName','ScanningSequence','SequenceVariant',
                        'ImageType','Rows','Columns','PixelSpacing','SliceThickness','SpacingBetweenSlices',
                        'RepetitionTime','EchoTime','InversionTime','MagneticFieldStrength','Manufacturer',
                        'ManufacturersModelName','ContrastBolusAgent','StudyDate','SeriesDate','AcquisitionDate']:
                r[tag] = val(tag)
            r['sample_same_series_uid'] = int(len({str(getattr(x, 'SeriesInstanceUID', '')) for x in ds}) == 1)
            r['sample_same_geometry'] = int(len({(str(getattr(x,'Rows','')),str(getattr(x,'Columns','')),
                str(getattr(x,'PixelSpacing','')),str(getattr(x,'ImageOrientationPatient',''))) for x in ds}) == 1)
            r['sample_date_matches_directory'] = int(str(getattr(d,'StudyDate','')) == key[1])
            r['sample_sha256'] = ';'.join(hashlib.sha256((destination/e['name']).read_bytes()).hexdigest() for e in sample_entries)
            r['sample_source_members'] = ';'.join(e['name'] for e in sample_entries)
            r['sample_matches_original_download_sha256'] = int(all(hashlib.sha256((destination/e['name']).read_bytes()).hexdigest()==original.get(e['name']) for e in sample_entries))
            text = ' '.join([key[2],r['SeriesDescription'],r['ProtocolName']]).upper()
            r['flair_metadata_candidate'] = int('FLAIR' in text)
            r['t1ce_metadata_candidate'] = int(any(t in text for t in ['T1GD','T1_GD','T1 GD','T1+GD','T1-GD','T1C','T1_C','T1 C','T1+C','T1_POST','T1 POST','T1-GAD','T1GAD']) or bool(r['ContrastBolusAgent'].strip()))
            r['sample_read_status'] = 'readable_headers'
        except Exception as exc:
            r['sample_read_status'] = f'{type(exc).__name__}: {exc}'
        records.append(r)
    output = ROOT / 'data/processed/dicom_sample_audit.csv'
    pd.DataFrame(records).to_csv(output, index=False)
    print('Wrote', output, 'directories', len(records), flush=True)


if __name__ == '__main__':
    main()
