"""Verify Stage14 receipts and preserve the already-published clinical reference."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import nbformat
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_mri_intake import CASES, SEQUENCES, sha256

REFERENCE_COMMIT = '739eddb5d4a4f9e4bdb3cde316c0ccefbbbe5794'
REFERENCE_FILES = [
    'data/raw/reference/ucsd_ptgbm_clinical_v3.xlsx',
    'data/raw/reference/ucsd_ptgbm_negative_cases.xlsx',
    'data/processed/ucsd_clinical_revalidated_cohort.csv',
    'data/processed/ucsd_clinical_revalidated_oof.csv',
    'reports/ucsd_clinical_revalidation/metrics.json',
    'outputs/ucsd-clinical-revalidation-20261029/UCSD_Clinical_Revalidation.xlsx',
    'src/rn_public/ucsd_clinical_revalidation.py',
    'notebooks/13_ucsd_clinical_revalidation.ipynb',
]


def main():
    result = json.loads((ROOT/'reports/ucsd_mri_intake/intake_receipt.json').read_text())
    s = result['summary']
    assert s['protocol_sha256'] == sha256(ROOT/'reports/ucsd_mri_intake_protocol.md')
    assert s['module_sha256'] == sha256(ROOT/'src/rn_public/ucsd_mri_intake.py')
    csv = pd.read_csv(ROOT/'reports/ucsd_mri_intake/sample_file_checklist.csv')
    assert len(csv) == len(result['files']) == 12
    assert set(csv.expected_filename) == {f'{case}_{seq}.nii.gz' for case in CASES for seq in SEQUENCES}
    for row, j in zip(csv.to_dict('records'), result['files']):
        for key in ['ID', 'sequence', 'expected_filename', 'minimal_batch', 'status', 'technical_pass', 'decoded']:
            assert row[key] == j[key], key
        for key in ['matches', 'issues']:
            assert json.loads(row[key]) == j[key]
        assert row['grid_status'] == j['grid_to_FLAIR']['status']
    assert s['decoded_expected_files'] == int(csv.decoded.sum())
    assert s['missing_expected_files'] == int(csv.status.eq('missing').sum())
    assert not s['ROI_for_prediction_approved'] and not s['MRI_model_fitted']
    tests = json.loads((ROOT/'reports/ucsd_mri_intake/software_test_receipt.json').read_text())
    assert tests['success'] and tests['failures'] == tests['errors'] == tests['skipped'] == 0
    assert tests['tests_run'] == 57 and tests['real_UCSD_images_validated_by_tests'] == 0
    nb = nbformat.read(ROOT/'notebooks/14_ucsd_mri_intake_and_qc.ipynb', as_version=4)
    nbformat.validate(nb)
    cells = [c for c in nb.cells if c.cell_type == 'code']
    code_hash = hashlib.sha256('\n'.join(c.source for c in cells).encode()).hexdigest()
    kernel = json.loads((ROOT/'reports/kernel_execution_14.json').read_text())
    assert kernel['success'] and len(kernel['notebooks']) == 1
    assert kernel['notebooks'][0]['code_sha256'] == code_hash
    assert kernel['notebooks'][0]['errors'] == 0 and len(cells) == 5
    assert [c.execution_count for c in cells] == [1, 2, 3, 4, 5]
    assert not any(o.output_type == 'error' for c in cells for o in c.outputs)
    preserved = {}
    for path in REFERENCE_FILES:
        old = subprocess.run(['git', 'show', f'{REFERENCE_COMMIT}:{path}'], cwd=ROOT,
                             check=True, capture_output=True).stdout
        assert old == (ROOT/path).read_bytes(), f'Prior clinical reference changed: {path}'
        preserved[path] = hashlib.sha256(old).hexdigest()
    verification = dict(success=True, intake_protocol_sha256=s['protocol_sha256'],
                        intake_module_sha256=s['module_sha256'], notebook_code_sha256=code_hash,
                        checklist_rows_verified=12, real_image_files_decoded=s['decoded_expected_files'],
                        MRI_model_fitted=False, source_authenticity_verified=False,
                        prior_clinical_reference_commit=REFERENCE_COMMIT,
                        byte_identical_prior_clinical_artifacts=preserved)
    output = ROOT/'reports/ucsd_mri_intake/artifact_verification.json'
    output.write_text(json.dumps(verification, indent=2)+'\n')
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
