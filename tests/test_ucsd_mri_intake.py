"""Synthetic fault-injection tests only. No generated array represents a patient."""
from pathlib import Path
import hashlib
import shutil
import sys
import tempfile
import unittest

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_mri_intake import CASES, audit_intake, compare_to_flair, inspect_nifti, run


class MRIIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic_MRI_software_test_')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name='fixture.nii.gz', data=None, affine=None, units='mm'):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            data = np.arange(120, dtype=np.float32).reshape(4, 5, 6)
        if affine is None:
            affine = np.eye(4)
        img = nib.Nifti1Image(data, affine)
        img.header.set_xyzt_units(units)
        img.set_qform(affine, 1)
        img.set_sform(affine, 1)
        nib.save(img, path)
        return path

    def test_missing_inputs_do_not_pass_and_remain_twelve_missing(self):
        a = audit_intake(self.root/'absent')
        self.assertEqual(a['summary']['missing_expected_files'], 12)
        self.assertEqual(a['summary']['decoded_expected_files'], 0)
        self.assertFalse(a['summary']['minimal_FLAIR_batch_technical_pass'])
        self.assertFalse(a['summary']['ROI_for_prediction_approved'])

    def test_full_decode_is_read_only_and_still_no_roi_authorization(self):
        for i, case in enumerate(CASES):
            self.write(f'{case}_FLAIR.nii.gz', data=np.arange(120, dtype=np.float32).reshape(4, 5, 6)+i)
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.glob('*.gz')}
        a = audit_intake(self.root)
        self.assertTrue(a['summary']['minimal_FLAIR_batch_technical_pass'])
        self.assertEqual(a['summary']['decoded_expected_files'], 2)
        self.assertFalse(a['summary']['ROI_for_prediction_approved'])
        self.assertFalse(a['summary']['source_authenticity_verified'])
        self.assertFalse(a['summary']['MRI_model_fitted'])
        self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.glob('*.gz')})

    def test_truncated_and_corrupt_gzip_and_html_placeholders_block(self):
        source = self.write().read_bytes()
        for data in [source[:-8], source[:-8]+b'\0'*8, b'<html>download page</html>', b'']:
            p = self.root/'broken.nii.gz'
            p.write_bytes(data)
            a = inspect_nifti(p)
            self.assertFalse(a['technical_pass'])
            self.assertFalse(a['decoded'])

    def test_nan_inf_constant_images_and_4d_cannot_pass(self):
        for data in [np.full((4, 5, 6), np.nan), np.full((4, 5, 6), np.inf),
                     np.zeros((4, 5, 6)), np.ones((4, 5, 6, 1))]:
            a = inspect_nifti(self.write(data=data.astype(np.float32)))
            self.assertFalse(a['technical_pass'])

    def test_unknown_units_and_qform_sform_disagreement_block(self):
        a = inspect_nifti(self.write(units='unknown'))
        self.assertIn('unknown_spatial_units', a['issues'])
        p = self.write()
        img = nib.load(p)
        affine = np.eye(4)
        affine[0, 3] = 2
        img.set_sform(affine, 1)
        nib.save(img, p)
        a = inspect_nifti(p)
        self.assertIn('qform_sform_disagreement', a['issues'])
        self.assertAlmostEqual(a['qform_sform_corner_delta_mm'], 2)
        self.assertFalse(a['technical_pass'])

    def test_world_grid_converts_meters_to_mm_but_rejects_translated_grid(self):
        ref = inspect_nifti(self.write('mm.nii.gz'))
        metric = inspect_nifti(self.write('meter.nii.gz', affine=np.diag([.001, .001, .001, 1]), units='meter'))
        self.assertEqual(compare_to_flair(metric, ref)['status'], 'grid_screen_pass')
        shifted = np.eye(4)
        shifted[0, 3] = 1
        other = inspect_nifti(self.write('shifted.nii.gz', affine=shifted))
        self.assertEqual(compare_to_flair(other, ref)['status'], 'grid_or_space_code_mismatch')
        self.assertFalse(compare_to_flair(metric, ref)['anatomical_alignment_verified'])

    def test_empty_fractional_negative_masks_block_without_tissue_code_guessing(self):
        for data in [np.zeros((4, 5, 6)), np.full((4, 5, 6), .5), -np.ones((4, 5, 6))]:
            a = inspect_nifti(self.write(data=data.astype(np.float32)), segmentation=True)
            self.assertFalse(a['technical_pass'])
        data = np.zeros((4, 5, 6), dtype=np.uint8)
        data[1, 2, 3] = 7
        a = inspect_nifti(self.write(data=data), segmentation=True)
        self.assertTrue(a['technical_pass'])
        self.assertEqual(a['observed_labels'], [0, 7])
        self.assertFalse(a['label_meanings_verified'])

    def test_duplicate_filename_and_byte_identical_cross_case_files_block(self):
        name = CASES[0]+'_FLAIR.nii.gz'
        p = self.write('one/'+name)
        self.write('two/'+name)
        a = audit_intake(self.root)
        self.assertEqual(a['files'][0]['status'], 'duplicate_filename')
        (self.root/'two'/name).unlink()
        shutil.copyfile(p, self.root/(CASES[1]+'_FLAIR.nii.gz'))
        a = audit_intake(self.root)
        self.assertFalse(a['summary']['minimal_FLAIR_batch_technical_pass'])
        self.assertIn('duplicate_content_requires_review', a['files'][0]['issues'])

    def test_parent_case_conflict_symlinks_and_outcome_masks_not_read(self):
        name = CASES[0]+'_FLAIR.nii.gz'
        p = self.write(CASES[1]+'/'+name)
        a = audit_intake(self.root)
        self.assertEqual(a['files'][0]['status'], 'directory_ID_conflict')
        (self.root/name).symlink_to(p)
        p.unlink()
        a = audit_intake(self.root)
        self.assertFalse(a['files'][0]['decoded'])
        forbidden = self.root/(CASES[0]+'_total_cellular_tumor_seg.nii.gz')
        forbidden.write_bytes(b'NOT AN IMAGE: parser must never read this outcome mask')
        a = audit_intake(self.root)
        self.assertEqual(a['excluded_files'][0]['reason'], 'prohibited_reference_mask_not_read')
        self.assertEqual(a['summary']['decoded_expected_files'], 0)

    def test_overlapping_input_output_does_not_write_into_input(self):
        with self.assertRaisesRegex(ValueError, 'must_be_separate'):
            run(ROOT, self.root, self.root/'reports')
        self.assertFalse((self.root/'reports').exists())


if __name__ == '__main__':
    unittest.main()
