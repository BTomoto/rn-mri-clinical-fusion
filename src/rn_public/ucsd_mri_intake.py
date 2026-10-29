"""Read-only two-case MRI intake. Technical checks never authorize prediction ROIs."""
from pathlib import Path
import csv
import datetime as dt
import gzip
import hashlib
import itertools
import json
import os
import re
import stat

import nibabel as nib
import numpy as np

CASES = ('UCSD-PTGBM-0001_01', 'UCSD-PTGBM-0003_01')
SEQUENCES = ('FLAIR', 'T1pre', 'T1post', 'T2', 'ADC_vendor', 'BraTS_tumor_seg')
FORBIDDEN = ('total_cellular_tumor_seg', 'enhancing_cellular_tumor_seg',
             'non_enhancing_cellular_tumor_seg')
MAX_BYTES = 512 * 1024**2
MAX_VOXELS = 40_000_000
TOLERANCE_MM = 0.1
UNIT_TO_MM = {'mm': 1.0, 'meter': 1000.0, 'micron': 0.001}
CASE_PATTERN = re.compile(r'UCSD-PTGBM-\d{4}_\d{2}')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def corner_delta(shape, a, b):
    corners = np.array(list(itertools.product(*[(0, int(n)-1) for n in shape])))
    return float(np.linalg.norm(nib.affines.apply_affine(a, corners) -
                                nib.affines.apply_affine(b, corners), axis=1).max())


def valid_affine(a):
    return (a is not None and np.shape(a) == (4, 4) and np.isfinite(a).all()
            and np.allclose(a[3], [0, 0, 0, 1]) and
            abs(np.linalg.det(a[:3, :3])) > 1e-12)


def inspect_nifti(path, segmentation=False):
    """No clinical labels; blocks ambiguous inputs and does not repair/resample."""
    path = Path(path)
    r = dict(technical_pass=False, decoded=False, issues=[], sha256=None)
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('not_regular_file_or_symlink')
        r['bytes'] = info.st_size
        if not 0 < info.st_size <= MAX_BYTES:
            raise ValueError('empty_or_file_size_limit')
        r['sha256'] = sha256(path)
        with gzip.open(path, 'rb') as f:
            decompressed = 0
            for block in iter(lambda: f.read(1024**2), b''):
                decompressed += len(block)
                if decompressed > MAX_BYTES:
                    raise ValueError('decompressed_size_limit')
        r['gzip_crc_verified'] = True
        img = nib.load(path, mmap=False)
        if not isinstance(img, (nib.Nifti1Image, nib.Nifti2Image)):
            raise ValueError('not_single_file_nifti')
        shape = tuple(int(n) for n in img.shape)
        r['shape'] = list(shape)
        if len(shape) != 3 or min(shape) < 2 or np.prod(shape, dtype=object) > MAX_VOXELS:
            raise ValueError('not_supported_3d_shape_or_voxel_limit')
        if img.get_data_dtype().kind not in 'iuf':
            raise ValueError('not_real_numeric_dtype')
        r['stored_dtype'] = str(img.get_data_dtype())
        r['proxy_scaling'] = dict(slope=float(img.dataobj.slope), intercept=float(img.dataobj.inter))
        units = img.header.get_xyzt_units()[0]
        r['spatial_units'] = units
        factor = UNIT_TO_MM.get(units)
        q, qc = img.get_qform(coded=True)
        s, sc = img.get_sform(coded=True)
        r['qform_code'], r['sform_code'] = int(qc), int(sc)
        r['selected_form_code'] = int(sc or qc)
        if not qc and not sc:
            r['issues'].append('fallback_coordinates_only')
        if factor is None:
            r['issues'].append('unknown_spatial_units')
        elif not valid_affine(img.affine):
            r['issues'].append('invalid_affine')
        else:
            a = np.array(img.affine, copy=True)
            a[:3] *= factor
            r['affine_mm'] = a.tolist()
            r['voxel_sizes_mm'] = nib.affines.voxel_sizes(a).tolist()
            r['orientation'] = list(nib.aff2axcodes(a))
            header_spacing = np.array(img.header.get_zooms()[:3]) * factor
            if not np.allclose(header_spacing, nib.affines.voxel_sizes(a), rtol=1e-4, atol=1e-4):
                r['issues'].append('header_affine_spacing_disagreement')
            r['matches_published_shape_spacing_only'] = bool(
                shape == (256, 256, 256) and np.allclose(nib.affines.voxel_sizes(a), 1, atol=1e-4))
            if qc and sc:
                if not valid_affine(q) or not valid_affine(s):
                    r['issues'].append('invalid_coded_form')
                else:
                    delta = corner_delta(shape, q, s) * factor
                    r['qform_sform_corner_delta_mm'] = delta
                    if delta > TOLERANCE_MM or qc != sc:
                        r['issues'].append('qform_sform_disagreement')
        # Force complete voxel access; nib.load alone is not evidence of decoding.
        data = img.get_fdata(dtype=np.float64, caching='unchanged')
        r['decoded'] = True
        finite = np.isfinite(data)
        r['nonfinite_voxels'] = int(data.size - np.count_nonzero(finite))
        if not finite.all():
            r['issues'].append('nonfinite_voxels')
        else:
            r['minimum'], r['maximum'] = float(data.min()), float(data.max())
            if segmentation:
                labels = np.unique(data)
                r['observed_labels'] = labels[:64].tolist()
                r['distinct_label_count'] = len(labels)
                r['label_meanings_verified'] = False
                r['nonzero_voxels'] = int(np.count_nonzero(data))
                if (labels < 0).any() or not np.equal(labels, np.rint(labels)).all():
                    r['issues'].append('segmentation_not_nonnegative_integer')
                if not r['nonzero_voxels']:
                    r['issues'].append('empty_segmentation_not_zero_feature')
                if len(labels) > 64:
                    r['issues'].append('too_many_segmentation_codes_for_intake')
            elif r['minimum'] == r['maximum']:
                r['issues'].append('constant_intensity_image')
        r['technical_pass'] = not r['issues']
    except Exception as exc:
        r['issues'].append(f'{type(exc).__name__}: {exc}')
    return r


def inventory(root):
    """No directory symlink traversal, and no archive extraction."""
    root = Path(root)
    if root.is_symlink():
        raise ValueError('intake_root_must_not_be_symlink')
    items = []
    if root.exists():
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(directory)/d).is_symlink())
            for name in sorted(files):
                p = Path(directory)/name
                if name.endswith(('.nii.gz', '.nii')):
                    items.append(p)
    return items


def compare_to_flair(row, reference):
    if not row.get('technical_pass') or not reference.get('technical_pass'):
        return dict(status='blocked_file_QC')
    if row['shape'] != reference['shape']:
        return dict(status='shape_mismatch')
    delta = corner_delta(row['shape'], row['affine_mm'], reference['affine_mm'])
    same = delta <= TOLERANCE_MM and row['selected_form_code'] == reference['selected_form_code']
    return dict(status='grid_screen_pass' if same else 'grid_or_space_code_mismatch',
                max_corner_delta_mm=delta, anatomical_alignment_verified=False)


def audit_intake(root):
    root = Path(root)
    paths = inventory(root)
    rows, ignored = [], []
    expected = {f'{case}_{seq}.nii.gz' for case in CASES for seq in SEQUENCES}
    for p in paths:
        if p.name not in expected:
            forbidden = any(p.name.endswith('_'+s+'.nii.gz') for s in FORBIDDEN)
            ignored.append(dict(path=p.relative_to(root).as_posix(),
                                reason='prohibited_reference_mask_not_read' if forbidden else 'outside_exact_sample_manifest'))
    for case in CASES:
        for seq in SEQUENCES:
            name = f'{case}_{seq}.nii.gz'
            matches = [p for p in paths if p.name == name]
            r = dict(ID=case, sequence=seq, expected_filename=name, minimal_batch=seq == 'FLAIR',
                     matches=[p.relative_to(root).as_posix() for p in matches],
                     status='missing', technical_pass=False, decoded=False, issues=[])
            if len(matches) > 1:
                r.update(status='duplicate_filename', issues=['ambiguous_duplicate_do_not_select'])
            elif len(matches) == 1:
                p = matches[0]
                parent_parts = (root.name,) + p.relative_to(root).parts[:-1]
                directory_ids = {m for part in parent_parts for m in CASE_PATTERN.findall(part)}
                if directory_ids - {case}:
                    r.update(status='directory_ID_conflict', issues=['filename_parent_case_disagreement'])
                else:
                    r.update(inspect_nifti(p, segmentation=seq == 'BraTS_tumor_seg'))
                    r['status'] = 'technical_pass' if r['technical_pass'] else 'requires_review'
            rows.append(r)
    # Byte-identical files across cases/sequences cannot silently pass as independent inputs.
    hashes = {}
    for r in rows:
        if r.get('sha256'):
            hashes.setdefault(r['sha256'], []).append(r)
    for group in hashes.values():
        if len(group) > 1:
            for r in group:
                r['issues'].append('duplicate_content_requires_review')
                r.update(technical_pass=False, status='requires_review')
    for case in CASES:
        ref = next(r for r in rows if r['ID'] == case and r['sequence'] == 'FLAIR')
        for r in (r for r in rows if r['ID'] == case):
            r['grid_to_FLAIR'] = compare_to_flair(r, ref)
    minimal = [r for r in rows if r['minimal_batch']]
    summary = dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   input_directory_exists=root.is_dir(), expected_files=len(rows),
                   missing_expected_files=sum(r['status'] == 'missing' for r in rows),
                   uniquely_located_expected_files=sum(len(r['matches']) == 1 for r in rows),
                   decoded_expected_files=sum(r['decoded'] for r in rows),
                   technical_pass_files=sum(r['technical_pass'] for r in rows),
                   minimal_FLAIR_batch_technical_pass=all(r['technical_pass'] for r in minimal),
                   expanded_batch_grid_screen_pass=all(r['grid_to_FLAIR']['status'] == 'grid_screen_pass' for r in rows),
                   source_authenticity_verified=False, anatomical_alignment_verified=False,
                   ROI_for_prediction_approved=False, MRI_features_extracted=False,
                   MRI_model_fitted=False, clinical_models_refitted=False,
                   nibabel_version=nib.__version__, numpy_version=np.__version__,
                   thresholds=dict(max_bytes=MAX_BYTES, max_voxels=MAX_VOXELS, corner_delta_mm=TOLERANCE_MM),
                   scope='Two selected technical cases only; no labels read by QC; no clinical or ROI acceptance')
    summary['state'] = 'awaiting_image_review_and_ROI_evidence' if summary['minimal_FLAIR_batch_technical_pass'] else 'blocked_missing_or_failed_sample_files'
    return dict(summary=summary, files=rows, excluded_files=ignored)


def run(project_root, input_root=None, output_root=None):
    project_root = Path(project_root)
    input_root = Path(input_root) if input_root is not None else project_root/'data/imaging/ucsd_samples'
    output_root = Path(output_root) if output_root is not None else project_root/'reports/ucsd_mri_intake'
    # Fail before writing if user accidentally points reports into the input tree.
    if output_root.resolve().is_relative_to(input_root.resolve()) or input_root.resolve().is_relative_to(output_root.resolve()):
        raise ValueError('input_and_output_directories_must_be_separate')
    result = audit_intake(input_root)
    for key, path in [('protocol_sha256', project_root/'reports/ucsd_mri_intake_protocol.md'),
                      ('module_sha256', Path(__file__))]:
        result['summary'][key] = sha256(path)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root/'intake_receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    fields = ['ID', 'sequence', 'expected_filename', 'minimal_batch', 'status', 'technical_pass',
              'decoded', 'matches', 'issues', 'sha256', 'bytes', 'shape', 'grid_status']
    with (output_root/'sample_file_checklist.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for r in result['files']:
            values = {k: r.get(k) for k in fields}
            values['grid_status'] = r['grid_to_FLAIR']['status']
            for key in ['matches', 'issues', 'shape']:
                values[key] = json.dumps(values[key], ensure_ascii=False)
            writer.writerow(values)
    return result
