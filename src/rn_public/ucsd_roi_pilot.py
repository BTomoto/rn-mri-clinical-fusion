"""Six-case technical pilot: label-independent ROI/normalisation operations, no models."""
from pathlib import Path
import concurrent.futures as cf
import datetime as dt
import json

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.spatial.distance import jensenshannon

from .ucsd_mri_intake import inspect_nifti, compare_to_flair, sha256
from .ucsd_mri_mirror import download_asset, compare_native_grid, SEQUENCE_ALIASES

SAMPLE_IDS = ('UCSD-PTGBM-0002_01', 'UCSD-PTGBM-0005_01', 'UCSD-PTGBM-0006_01',
              'UCSD-PTGBM-0007_01', 'UCSD-PTGBM-0008_02', 'UCSD-PTGBM-0010_01')
STRUCTURAL = ('FLAIR', 'T1pre', 'T1post', 'T2')
N_BINS = 32


def region_union(seg):
    a = np.asarray(seg)
    if a.ndim != 3 or not np.isfinite(a).all() or (a < 0).any() or not np.equal(a, np.rint(a)).all():
        raise ValueError('invalid_segmentation_values')
    mask = a > 0
    if not mask.any():
        raise ValueError('empty_source_annotation_union')
    return mask


def percentile_parameters(image):
    a = np.asarray(image)
    if a.ndim != 3 or not np.isfinite(a).all():
        raise ValueError('nonfinite_or_non3d_image')
    support = a[a > 0]
    if not support.size:
        raise ValueError('empty_nonzero_intensity_support')
    low, high = np.percentile(support, [1, 99], method='linear')
    if high <= low:
        raise ValueError('degenerate_percentile_range')
    return dict(p01=float(low), p99=float(high), support_voxels=int(support.size))


def normalize_values(values, params):
    a = np.asarray(values, dtype=np.float64)
    if not np.isfinite(a).all() or params['p99'] <= params['p01']:
        raise ValueError('normalisation_input_invalid')
    return np.clip((a-params['p01'])/(params['p99']-params['p01']), 0, 1)


def fixed_bins(values, minimum=None, maximum=None):
    v = np.asarray(values, dtype=np.float64)
    if not v.size or not np.isfinite(v).all():
        raise ValueError('empty_or_nonfinite_ROI_intensity')
    lo = float(v.min()) if minimum is None else float(minimum)
    hi = float(v.max()) if maximum is None else float(maximum)
    if hi <= lo:
        raise ValueError('constant_ROI_intensity')
    # IBSI FBN: maximum is explicitly assigned to the last bin.
    bins = np.floor(N_BINS*(v-lo)/(hi-lo)).astype(int)+1
    bins = np.clip(bins, 1, N_BINS)
    return bins, lo, hi


def intensity_diagnostics(image, roi, eroded):
    a = np.asarray(image)
    if a.shape != roi.shape or eroded.shape != roi.shape or not roi.any() or (eroded & ~roi).any():
        raise ValueError('ROI_shape_or_subset_invalid')
    params = percentile_parameters(a)  # Does not read ROI, class, or any other patient.
    raw = a[roi]
    values = normalize_values(raw, params)
    result = dict(**params, roi_voxels=int(roi.sum()), raw_roi_zero_fraction=float(np.mean(raw == 0)),
                  clipped_low_fraction=float(np.mean(raw < params['p01'])),
                  clipped_high_fraction=float(np.mean(raw > params['p99'])),
                  normalized_minimum=float(values.min()), normalized_maximum=float(values.max()),
                  normalized_mean=float(values.mean()), normalized_std=float(values.std()),
                  raw_distinct_values=int(np.unique(raw).size), normalisation_success=True,
                  histogram_success=False, histogram_error=None, occupied_bins=None,
                  eroded_voxels=int(eroded.sum()), erosion_histogram_success=False,
                  erosion_JS_distance=None, bins=N_BINS, normalization_uses_ROI=False,
                  normalization_uses_clinical_label=False)
    try:
        b, lo, hi = fixed_bins(values)
        count = np.bincount(b, minlength=N_BINS+1)[1:]
        result.update(histogram_success=True, occupied_bins=int(np.count_nonzero(count)),
                      bin_minimum=lo, bin_maximum=hi, bin_counts=count.tolist(),
                      bin_probabilities=(count/count.sum()).tolist())
        if eroded.any():
            ev = normalize_values(a[eroded], params)
            eb, _, _ = fixed_bins(ev, minimum=lo, maximum=hi)
            ec = np.bincount(eb, minlength=N_BINS+1)[1:]
            result.update(erosion_histogram_success=True,
                          eroded_bin_counts=ec.tolist(),
                          erosion_JS_distance=float(jensenshannon(count/count.sum(), ec/ec.sum(), base=2)))
        else:
            result['erosion_error'] = 'empty_eroded_ROI'
    except ValueError as exc:
        result['histogram_error'] = str(exc)
    return result


def sample_binding(root):
    cohort = pd.read_csv(Path(root)/'data/processed/ucsd_clinical_revalidated_cohort.csv')
    meta = pd.read_csv(Path(root)/'data/raw/reference/ucsd_mirror_participants.tsv', sep='\t', encoding='cp1252')
    meta['clinical_ID'] = meta.ID.str.replace('sub-', 'UCSD-PTGBM-', regex=False)
    if meta.clinical_ID.duplicated().any():
        raise ValueError('duplicate_mirror_metadata_ID')
    rows = []
    for case in SAMPLE_IDS:
        a = cohort[cohort.ID.eq(case)]
        b = meta[meta.clinical_ID.eq(case)]
        if len(a) != 1 or len(b) != 1 or a.iloc[0]['BraTS ID'] != b.iloc[0]['BraTS ID']:
            raise ValueError('sample_ID_binding_failed: '+case)
        r = a.iloc[0]
        rows.append(dict(ID=case, patient_id=r.patient_id, brats_ID=r['BraTS ID'],
                         tumor_label=int(r.tumor_label), label_source=r.label_source,
                         two_IDs_match=True))
    d = pd.DataFrame(rows)
    if d.patient_id.nunique() != 6 or d.tumor_label.value_counts().to_dict() != {0: 3, 1: 3}:
        raise ValueError('six_distinct_patients_and_three_per_class_required')
    return d


def source_qc(root, manifest):
    rows = []
    for r in manifest.to_dict('records'):
        path = Path(root)/'data/samples/ucsd_mirror'/r['mirror_filename']
        q = inspect_nifti(path, segmentation=r['sequence'] == 'BraTS_tumor_seg')
        if q['decoded']:
            img = nib.load(path)
            q.update(native_affine=img.affine.tolist(), native_voxel_steps=list(map(float, img.header.get_zooms()[:3])),
                     native_orientation=list(nib.aff2axcodes(img.affine)))
        q['release_digest_matches'] = q.get('sha256') == r['sha256']
        if not q['release_digest_matches']:
            q['technical_pass'] = False
            q['issues'].append('release_digest_mismatch')
        rows.append(dict(ID=r['ID'], sequence=r['sequence'], filename=r['mirror_filename'],
                         path=path.relative_to(root).as_posix(), **q))
    for case in SAMPLE_IDS:
        ref = next(r for r in rows if r['ID'] == case and r['sequence'] == 'FLAIR')
        for r in [x for x in rows if x['ID'] == case]:
            r['physical_grid'] = compare_to_flair(r, ref)
            r['relative_grid'] = compare_native_grid(r, ref)
    return rows


def process_case(root, case, files):
    f = {r['sequence']: r for r in files if r['ID'] == case}
    required = [f[s] for s in (*STRUCTURAL, 'BraTS_tumor_seg')]
    for r in required:
        issues = [x for x in r['issues'] if x != 'unknown_spatial_units']
        if (not r['decoded'] or not r['release_digest_matches'] or issues or
                r['relative_grid']['status'] != 'native_matrix_match'):
            raise ValueError('required_file_not_eligible_for_native_array_pilot: '+r['sequence'])
    source = nib.load(Path(root)/f['BraTS_tumor_seg']['path'])
    seg = np.asarray(source.dataobj)
    roi = region_union(seg)
    eroded = ndimage.binary_erosion(roi, structure=ndimage.generate_binary_structure(3, 1), iterations=1)
    _, ncomp = ndimage.label(roi, structure=np.ones((3, 3, 3), dtype=bool))
    derived = Path(root)/'data/processed/ucsd_roi_pilot_masks'/f'{case}_annotation_union.nii.gz'
    derived.parent.mkdir(parents=True, exist_ok=True)
    header = source.header.copy();header.set_data_dtype(np.uint8)
    header.set_slope_inter(1, 0)
    nib.save(nib.Nifti1Image(roi.astype(np.uint8), source.affine, header=header), derived)
    case_record = dict(ID=case, roi_nonempty=True, roi_voxels=int(roi.sum()),
                       array_fraction=float(roi.mean()), components_26=int(ncomp),
                       observed_codes=json.dumps(np.unique(seg).tolist()),
                       erosion_voxels=int(eroded.sum()), erosion_retention=float(eroded.sum()/roi.sum()),
                       physical_volume_computed=False, pure_tumor_interpretation=False,
                       roi_rule='all_positive_ordinary_BraTS_codes_union',
                       derived_mask=derived.relative_to(root).as_posix(), derived_mask_sha256=sha256(derived),
                       spatial_units=source.header.get_xyzt_units()[0], success=True, error=None)
    params = []
    for seq in STRUCTURAL:
        img = nib.load(Path(root)/f[seq]['path'])
        q = intensity_diagnostics(np.asarray(img.dataobj), roi, eroded)
        params.append(dict(ID=case, sequence=seq, **q))
    return case_record, params


def run(root):
    root = Path(root);out = root/'reports/ucsd_roi_pilot';out.mkdir(parents=True, exist_ok=True)
    binding = sample_binding(root)
    inv = pd.read_csv(root/'data/metadata/ucsd_mirror_asset_inventory.csv')
    manifest = inv[inv.ID.isin(SAMPLE_IDS)].sort_values(['ID', 'sequence'])
    if (len(manifest) != 36 or manifest.duplicated(['ID', 'sequence']).any() or
            set(manifest.sequence) != set(SEQUENCE_ALIASES.values()) or manifest.bytes.sum() > 80*1024**2):
        raise ValueError('six_case_manifest_invalid')
    manifest.to_csv(out/'source_manifest.csv', index=False)
    def get(r):
        result = dict(ID=r['ID'], sequence=r['sequence'], success=False)
        try:
            record = download_asset(r, root/'data/samples/ucsd_mirror'/r['mirror_filename'])
            record['path'] = Path(record['path']).relative_to(root).as_posix()
            result.update(record, success=True)
        except Exception as exc:
            result['error'] = type(exc).__name__+': '+str(exc)
        return result
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        transfers = list(pool.map(get, manifest.to_dict('records')))
    (out/'download_receipt.json').write_text(json.dumps(dict(
        checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), files=transfers), indent=2)+'\n')
    files = source_qc(root, manifest)
    cases, params = [], []
    for case in SAMPLE_IDS:
        try:
            row, records = process_case(root, case, files)
            cases.append(row);params.extend(records)
        except Exception as exc:
            cases.append(dict(ID=case, success=False, error=type(exc).__name__+': '+str(exc)))
    case_table = binding.merge(pd.DataFrame(cases), on='ID', validate='one_to_one')
    case_table.to_csv(out/'case_ROI_diagnostics.csv', index=False)
    long_rows, flat = [], []
    for r in params:
        flat.append({k: v for k, v in r.items() if not isinstance(v, list)})
        if r['histogram_success']:
            for b, (n, p) in enumerate(zip(r['bin_counts'], r['bin_probabilities']), 1):
                long_rows.append(dict(ID=r['ID'], sequence=r['sequence'], bin=b,
                                      voxel_count=n, probability=p,
                                      eroded_voxel_count=r.get('eroded_bin_counts', [None]*N_BINS)[b-1]))
    pd.DataFrame(flat).to_csv(out/'normalization_diagnostics.csv', index=False)
    pd.DataFrame(long_rows).to_csv(out/'fixed_32_bin_histograms.csv', index=False)
    qflat = []
    for r in files:
        qflat.append(dict(ID=r['ID'], sequence=r['sequence'], filename=r['filename'],
                          bytes=r.get('bytes'), sha256=r.get('sha256'), decoded=r['decoded'],
                          digest_matches=r['release_digest_matches'], physical_QC_pass=r['technical_pass'],
                          relative_grid_status=r['relative_grid']['status'],
                          shape='x'.join(map(str, r.get('shape', []))), spatial_units=r.get('spatial_units'),
                          dtype=r.get('stored_dtype'), minimum=r.get('minimum'), maximum=r.get('maximum'),
                          nonfinite_voxels=r.get('nonfinite_voxels'), issues='; '.join(r['issues']), path=r['path']))
    pd.DataFrame(qflat).to_csv(out/'source_file_QC.csv', index=False)
    summary = dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), sample_cases=6, source_patients=6,
                   source_files_requested=36, source_files_available=sum(x['success'] for x in transfers),
                   source_bytes_available=sum(x.get('bytes', 0) for x in transfers if x['success']),
                   source_files_decoded=sum(x['decoded'] for x in files),
                   source_relative_grid_matches=sum(x['relative_grid']['status'] == 'native_matrix_match' for x in files),
                   source_physical_QC_pass=sum(x['technical_pass'] for x in files),
                   source_units_unknown=sum(x.get('spatial_units') == 'unknown' for x in files),
                   source_uint8_intensity_files=sum(x.get('stored_dtype') == 'uint8' and x['sequence'] != 'BraTS_tumor_seg' for x in files),
                   ROI_processing_success=sum(x['success'] for x in cases),
                   structural_normalizations_success=sum(x['normalisation_success'] for x in params),
                   histogram_success=sum(x['histogram_success'] for x in params),
                   erosion_histogram_success=sum(x['erosion_histogram_success'] for x in params),
                   normalization_parameters_fitted_across_patients=False,
                   normalization_parameters_use_ROI=False, ROI_rule_uses_class=False,
                   source_annotation_blinding_confirmed=False, pure_tumor_ROI=False,
                   physical_units_confirmed=False, anatomical_alignment_accepted=False,
                   clinical_model_refitted=False, MRI_model_fitted=False, MRI_performance_estimated=False,
                   whole_cohort_downloaded=False, next_step_requires_user_approval=True,
                   protocol_sha256=sha256(root/'reports/ucsd_roi_pilot_protocol.md'),
                   code_sha256=sha256(Path(__file__)))
    (out/'pilot_receipt.json').write_text(json.dumps(dict(summary=summary, files=files, cases=cases,
                                                        normalization=params), indent=2, allow_nan=False)+'\n')
    return summary
