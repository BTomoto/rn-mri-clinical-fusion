"""Prevent alias/identity errors and accidental conversion of unknown units to mm."""
from pathlib import Path
import sys
import unittest
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_mri_mirror import asset_record, bind_sample_metadata, compare_native_grid, coverage_table, SAMPLE_IDS


class MirrorTests(unittest.TestCase):
    def test_exact_aliases_and_outcome_masks_are_not_download_candidates(self):
        a = dict(name='sub-0002_ses-01_run-post_T1w.nii.gz', id=1, size=10,
                 digest='sha256:'+'a'*64, browser_download_url='https://github.com/example')
        r = asset_record(a, 'tag')
        self.assertEqual((r['ID'], r['sequence']), ('UCSD-PTGBM-0002_01', 'T1post'))
        for name in ['sub-0002_ses-01_total_cellular_tumor_seg.nii.gz',
                     'sub-0002_ses-01_non_enhancing_cellular_tumor_seg.nii.gz',
                     'sub-0002_ses-01_enhancing_cellular_tumor_seg.nii.gz',
                     '../sub-0002_ses-01_FLAIR.nii.gz']:
            self.assertIsNone(asset_record(dict(a, name=name), 'tag'))

    def test_native_match_does_not_turn_unknown_units_into_physical_acceptance(self):
        r = dict(decoded=True, shape=[4, 5, 6], native_affine=np.eye(4).tolist(),
                 spatial_units='unknown', selected_form_code=1)
        c = compare_native_grid(r, r)
        self.assertEqual(c['status'], 'native_matrix_match')
        self.assertFalse(c['physical_units_confirmed'])
        a = np.eye(4);a[0, 3] = 1
        self.assertEqual(compare_native_grid(dict(r, native_affine=a.tolist()), r)['status'], 'native_grid_mismatch')
        self.assertEqual(compare_native_grid(dict(r, decoded=False), r)['status'], 'blocked_not_decoded')

    def test_patient_mapping_rejects_duplicate_and_cross_namespace_mismatch(self):
        c = pd.read_csv(ROOT/'data/processed/ucsd_clinical_revalidated_cohort.csv')
        m = c[c.ID.isin(SAMPLE_IDS)][['ID', 'BraTS ID']].copy()
        m.ID = m.ID.str.replace('UCSD-PTGBM-', 'sub-', regex=False)
        self.assertEqual(len(bind_sample_metadata(c, m)), 2)
        with self.assertRaisesRegex(ValueError, 'duplicate_metadata'):
            bind_sample_metadata(c, pd.concat([m, m.iloc[:1]]))
        m.loc[m.index[0], 'BraTS ID'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            bind_sample_metadata(c, m)

    def test_listing_coverage_is_never_counted_as_downloaded_data(self):
        c = pd.read_csv(ROOT/'data/processed/ucsd_clinical_revalidated_cohort.csv')
        inv = pd.DataFrame([dict(ID=SAMPLE_IDS[0], sequence='FLAIR')])
        result = coverage_table(c, inv)
        self.assertEqual(result.listed_FLAIR.sum(), 1)
        self.assertEqual(result.listed_all_six.sum(), 0)
        self.assertEqual(result.actual_download_complete.sum(), 0)
        self.assertEqual(len(result), 238)
        with self.assertRaisesRegex(ValueError, 'duplicate_sequence'):
            coverage_table(c, pd.concat([inv, inv]))


if __name__ == '__main__':
    unittest.main()
