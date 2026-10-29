"""Small, fixed HTTPS mirror sample; clinical labels are never inferred from masks."""
from pathlib import Path
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import re
import urllib.request

import nibabel as nib
import numpy as np
import pandas as pd

from .ucsd_mri_intake import inspect_nifti, compare_to_flair, sha256, valid_affine, corner_delta

RELEASE_TAGS = ('ucsd-ptgbm', 'ucsd-ptgbm_1', 'ucsd-ptgbm_2', 'ucsd-ptgbm_3', 'ucsd-ptgbm_4')
SEQUENCE_ALIASES = {'FLAIR': 'FLAIR', 'run-pre_T1w': 'T1pre', 'run-post_T1w': 'T1post',
                    'T2w': 'T2', 'ADC_vendor': 'ADC_vendor', 'BraTS_tumor_seg': 'BraTS_tumor_seg'}
SAMPLE_IDS = ('UCSD-PTGBM-0002_01', 'UCSD-PTGBM-0005_01')
NAME = re.compile(r'^sub-(\d{4})_ses-(\d{2})_(.+)\.nii\.gz$')
HEADERS = {'User-Agent': 'RNPublicDataAudit/1.0'}
MAX_FILE_BYTES = 20 * 1024**2
MAX_TOTAL_BYTES = 40 * 1024**2


def asset_record(asset, tag):
    m = NAME.fullmatch(asset.get('name', ''))
    if not m or m[3] not in SEQUENCE_ALIASES:
        return None
    return dict(ID=f'UCSD-PTGBM-{m[1]}_{m[2]}', sequence=SEQUENCE_ALIASES[m[3]],
                mirror_filename=asset['name'], release_tag=tag, asset_id=asset['id'],
                bytes=int(asset['size']), sha256=asset['digest'].removeprefix('sha256:'),
                url=asset['browser_download_url'])


def refresh_inventory(root):
    """Only list known public releases; retain relevant six-sequence metadata."""
    records, receipts = [], []
    metadata = None
    def get(tag):
        url = 'https://api.github.com/repos/data-nih/tcia/releases/tags/'+tag
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=25) as r:
            return tag, json.load(r)
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(get, RELEASE_TAGS))
    for tag, j in results:
        receipts.append(dict(tag=tag, release_id=j['id'], published_at=j['published_at'],
                             updated_at=j['updated_at'], assets_listed=len(j.get('assets', []))))
        for a in j.get('assets', []):
            if a['name'] == 'participants.tsv':
                metadata = dict(ID='metadata', sequence='participants', mirror_filename=a['name'],
                                bytes=a['size'], sha256=a['digest'].removeprefix('sha256:'),
                                url=a['browser_download_url'])
            rec = asset_record(a, tag)
            if rec:
                records.append(rec)
    if metadata is None:
        raise ValueError('participants_metadata_not_listed')
    d = pd.DataFrame(records).sort_values(['ID', 'sequence']).reset_index(drop=True)
    if d.duplicated(['ID', 'sequence']).any():
        raise ValueError('ambiguous_case_sequence_in_mirror')
    if not d.sha256.str.fullmatch('[0-9a-f]{64}').all():
        raise ValueError('missing_release_digest')
    out = Path(root)/'data/metadata'
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out/'ucsd_mirror_asset_inventory.csv', index=False)
    (out/'ucsd_mirror_inventory_receipt.json').write_text(json.dumps(dict(
        checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), releases=receipts,
        relevant_file_entries=len(d), participants_asset=metadata,
        route='public GitHub release HTTPS', original_TCIA_byte_identity_checked=False), indent=2)+'\n')
    return d, metadata


def download_asset(record, dest):
    """Check mirror-declared bytes/hash. This does not assert original TCIA identity."""
    dest = Path(dest)
    expected_size = int(record['bytes'])
    if not 0 < expected_size <= MAX_FILE_BYTES:
        raise ValueError('sample_file_size_limit')
    if dest.exists() and dest.stat().st_size == expected_size and sha256(dest) == record['sha256']:
        return dict(path=dest.as_posix(), bytes=expected_size, sha256=record['sha256'],
                    release_digest_matches=True, reused=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name+'.partial')
    errors = []
    for attempt in range(2):
        try:
            req = urllib.request.Request(record['url'], headers=HEADERS)
            h, size = hashlib.sha256(), 0
            with urllib.request.urlopen(req, timeout=25) as r, part.open('wb') as f:
                if r.status != 200:
                    raise ValueError('unexpected_download_status')
                for block in iter(lambda: r.read(1024**2), b''):
                    size += len(block)
                    if size > expected_size:
                        raise ValueError('download_larger_than_declared')
                    h.update(block)
                    f.write(block)
            if size != expected_size or h.hexdigest() != record['sha256']:
                raise ValueError('download_size_or_release_digest_mismatch')
            part.replace(dest)
            return dict(path=dest.as_posix(), bytes=size, sha256=h.hexdigest(),
                        release_digest_matches=True, reused=False, attempts=attempt+1)
        except Exception as exc:
            part.unlink(missing_ok=True)
            errors.append(type(exc).__name__+': '+str(exc))
    raise RuntimeError('; '.join(errors))


def coverage_table(cohort, inventory):
    if inventory.duplicated(['ID', 'sequence']).any():
        raise ValueError('duplicate_sequence_not_resolved')
    d = cohort[['ID', 'patient_id', 'BraTS ID', 'tumor_label', 'label_source']].copy()
    for seq in SEQUENCE_ALIASES.values():
        d['listed_'+seq] = d.ID.isin(inventory.loc[inventory.sequence.eq(seq), 'ID'])
    d['listed_all_six'] = d[['listed_'+s for s in SEQUENCE_ALIASES.values()]].all(axis=1)
    d['selected_technical_sample'] = d.ID.isin(SAMPLE_IDS)
    d['actual_download_complete'] = False  # filled only from successful file receipts later
    return d


def bind_sample_metadata(cohort, metadata):
    """Two identifier namespaces, no inferred labels and no clinical table replacement."""
    m = metadata.copy()
    if not m.ID.astype(str).str.fullmatch(r'sub-\d{4}_\d{2}').all():
        raise ValueError('unexpected_metadata_ID_format')
    m['clinical_ID'] = m.ID.str.replace('sub-', 'UCSD-PTGBM-', regex=False)
    if m.clinical_ID.duplicated().any():
        raise ValueError('duplicate_metadata_case_ID')
    out = []
    for case in SAMPLE_IDS:
        a = cohort.loc[cohort.ID.eq(case)]
        b = m.loc[m.clinical_ID.eq(case)]
        if len(a) != 1 or len(b) != 1 or a.iloc[0]['BraTS ID'] != b.iloc[0]['BraTS ID']:
            raise ValueError('sample_case_or_BraTS_ID_mismatch: '+case)
        out.append(dict(ID=case, mirror_metadata_ID=b.iloc[0].ID, brats_ID=a.iloc[0]['BraTS ID'],
                        patient_id=a.iloc[0].patient_id, tumor_label=int(a.iloc[0].tumor_label),
                        label_source=a.iloc[0].label_source, two_identifier_fields_match=True))
    if len({r['patient_id'] for r in out}) != 2:
        raise ValueError('samples_not_two_distinct_source_patients')
    return out


def compare_native_grid(row, reference):
    """Numerical relative-grid check without assigning a missing physical unit."""
    if not row.get('decoded') or not reference.get('decoded'):
        return dict(status='blocked_not_decoded')
    if row.get('shape') != reference.get('shape'):
        return dict(status='shape_mismatch')
    a, b = row.get('native_affine'), reference.get('native_affine')
    if not valid_affine(np.asarray(a)) or not valid_affine(np.asarray(b)):
        return dict(status='invalid_native_affine')
    delta = corner_delta(row['shape'], a, b)
    same = (row.get('spatial_units') == reference.get('spatial_units') and
            row.get('selected_form_code') == reference.get('selected_form_code') and delta <= 1e-6)
    return dict(status='native_matrix_match' if same else 'native_grid_mismatch',
                max_corner_delta_native=delta, physical_units_confirmed=False,
                anatomical_alignment_verified=False)


def sample_qc(root, selected):
    results = []
    for r in selected.to_dict('records'):
        path = Path(root)/'data/samples/ucsd_mirror'/r['mirror_filename']
        q = inspect_nifti(path, segmentation=r['sequence'] == 'BraTS_tumor_seg')
        if q['decoded']:
            img = nib.load(path)
            q['native_affine'] = img.affine.tolist()
            q['native_voxel_steps'] = list(map(float, img.header.get_zooms()[:3]))
            q['native_orientation'] = list(nib.aff2axcodes(img.affine))
        q['release_digest_matches'] = q.get('sha256') == r['sha256']
        if not q['release_digest_matches']:
            q['technical_pass'] = False
            q['issues'].append('release_digest_mismatch_or_file_missing')
        results.append(dict(ID=r['ID'], sequence=r['sequence'], filename=r['mirror_filename'],
                            relative_path=path.relative_to(root).as_posix(),
                            mirror_sha256=r['sha256'], **q))
    hashes = {}
    for r in results:
        if r.get('sha256'):
            hashes.setdefault(r['sha256'], []).append(r)
    for rows in hashes.values():
        if len(rows) > 1:
            for r in rows:
                r['technical_pass'] = False
                r['issues'].append('duplicate_content_requires_review')
    for case in SAMPLE_IDS:
        ref = next(r for r in results if r['ID'] == case and r['sequence'] == 'FLAIR')
        for r in (r for r in results if r['ID'] == case):
            r['grid_to_FLAIR'] = compare_to_flair(r, ref)
            r['relative_grid_to_FLAIR'] = compare_native_grid(r, ref)
    return results


def run(root, refresh=False):
    root = Path(root)
    out = root/'reports/ucsd_mri_mirror'
    out.mkdir(parents=True, exist_ok=True)
    if refresh:
        inv, metadata_asset = refresh_inventory(root)
    else:
        inv = pd.read_csv(root/'data/metadata/ucsd_mirror_asset_inventory.csv')
        metadata_asset = json.loads((root/'data/metadata/ucsd_mirror_inventory_receipt.json').read_text())['participants_asset']
    metadata_path = root/'data/raw/reference/ucsd_mirror_participants.tsv'
    meta_download = download_asset(metadata_asset, metadata_path)
    meta_download['path'] = metadata_path.relative_to(root).as_posix()
    metadata = pd.read_csv(metadata_path, sep='\t', encoding='cp1252')
    cohort = pd.read_csv(root/'data/processed/ucsd_clinical_revalidated_cohort.csv')
    bindings = bind_sample_metadata(cohort, metadata)
    selected = inv[inv.ID.isin(SAMPLE_IDS)].copy().sort_values(['ID', 'sequence'])
    if len(selected) != 12 or selected.groupby('ID').sequence.nunique().ne(6).any():
        raise ValueError('fixed_twelve_file_manifest_incomplete')
    if selected.bytes.sum() > MAX_TOTAL_BYTES:
        raise ValueError('sample_total_size_limit')
    selected.to_csv(out/'selected_download_manifest.csv', index=False)
    downloads = []
    def one(record):
        r = dict(ID=record['ID'], sequence=record['sequence'], filename=record['mirror_filename'],
                 url=record['url'], success=False)
        try:
            result = download_asset(record, root/'data/samples/ucsd_mirror'/record['mirror_filename'])
            result['path'] = Path(result['path']).relative_to(root).as_posix()
            r.update(result, success=True)
        except Exception as exc:
            r['error'] = type(exc).__name__+': '+str(exc)
        return r
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        downloads = list(pool.map(one, selected.to_dict('records')))
    # Always preserve transfer evidence before any later decoding failure.
    (out/'download_receipt.json').write_text(json.dumps(dict(
        checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), metadata=meta_download,
        files=downloads), indent=2)+'\n')
    qc = sample_qc(root, selected)
    coverage = coverage_table(cohort, inv)
    completed = {case for case in SAMPLE_IDS if all(d['success'] for d in downloads if d['ID'] == case)}
    coverage['actual_download_complete'] = coverage.ID.isin(completed)
    coverage.to_csv(out/'clinical_mirror_sequence_coverage.csv', index=False)
    pd.DataFrame(bindings).to_csv(out/'sample_case_mapping.csv', index=False)
    flat = []
    for r in qc:
        spacing = r.get('voxel_sizes_mm', [None]*3)
        flat.append(dict(ID=r['ID'], sequence=r['sequence'], filename=r['filename'],
                         bytes=r.get('bytes'), sha256=r.get('sha256'), decoded=r['decoded'],
                         technical_pass=r['technical_pass'], issues='; '.join(r['issues']),
                         shape='x'.join(map(str, r.get('shape', []))),
                         spacing_x_mm=spacing[0], spacing_y_mm=spacing[1], spacing_z_mm=spacing[2],
                         stored_dtype=r.get('stored_dtype'), spatial_units=r.get('spatial_units'),
                         orientation=''.join(r.get('orientation', [])),
                         minimum=r.get('minimum'), maximum=r.get('maximum'),
                         nonfinite_voxels=r.get('nonfinite_voxels'),
                         observed_labels=json.dumps(r.get('observed_labels')),
                         native_voxel_steps=json.dumps(r.get('native_voxel_steps')),
                         native_orientation=''.join(r.get('native_orientation', [])),
                         relative_grid_status=r['relative_grid_to_FLAIR']['status'],
                         grid_status=r['grid_to_FLAIR']['status'],
                         grid_corner_delta_mm=r['grid_to_FLAIR'].get('max_corner_delta_mm')))
    pd.DataFrame(flat).to_csv(out/'sample_file_qc.csv', index=False)
    summary = dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   route='public GitHub release HTTPS; no Aspera', sample_IDs=list(SAMPLE_IDS),
                   requested_image_files=12, successful_download_files=sum(d['success'] for d in downloads),
                   downloaded_image_bytes=sum(d.get('bytes', 0) for d in downloads if d['success']),
                   decoded_image_files=sum(r['decoded'] for r in qc),
                   technical_pass_image_files=sum(r['technical_pass'] for r in qc),
                   grid_screen_pass_files=sum(r['grid_to_FLAIR']['status'] == 'grid_screen_pass' for r in qc),
                   relative_native_grid_matches=sum(r['relative_grid_to_FLAIR']['status'] == 'native_matrix_match' for r in qc),
                   unknown_spatial_unit_files=sum(r.get('spatial_units') == 'unknown' for r in qc),
                   uint8_intensity_files=sum(r['sequence'] != 'BraTS_tumor_seg' and r.get('stored_dtype') == 'uint8' for r in qc),
                   sample_two_ID_bindings_match=all(b['two_identifier_fields_match'] for b in bindings),
                   mirror_listed_FLAIR_timepoints=int(inv.loc[inv.sequence.eq('FLAIR'), 'ID'].nunique()),
                   remaining_clinical_timepoints=len(cohort), remaining_clinical_patients=int(cohort.patient_id.nunique()),
                   listed_all_six_remaining_timepoints=int(coverage.listed_all_six.sum()),
                   listed_all_six_remaining_patients=int(coverage.loc[coverage.listed_all_six, 'patient_id'].nunique()),
                   listed_all_six_tumor_timepoints=int(coverage.loc[coverage.listed_all_six, 'tumor_label'].sum()),
                   listed_all_six_treatment_change_timepoints=int((coverage.listed_all_six & coverage.tumor_label.eq(0)).sum()),
                   entire_mirror_downloaded=False, clinical_models_refitted=False, MRI_model_fitted=False,
                   prediction_features_extracted=False, ROI_for_prediction_approved=False,
                   anatomical_alignment_accepted=False, original_TCIA_byte_identity_required=False,
                   original_TCIA_byte_identity_checked=False,
                   plan_sha256=sha256(root/'reports/ucsd_mri_mirror_sample_plan.md'),
                   code_sha256=sha256(Path(__file__)))
    (out/'sample_qc_receipt.json').write_text(json.dumps(dict(summary=summary, files=qc, case_mapping=bindings), indent=2, allow_nan=False)+'\n')
    return summary
