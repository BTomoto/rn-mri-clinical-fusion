"""Small array tests of ROI integrity, normalization leakage and FBN boundaries."""
from pathlib import Path
import sys,unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_roi_pilot import region_union, percentile_parameters, normalize_values, fixed_bins, intensity_diagnostics, sample_binding
from rn_public.ucsd_intensity_followup import affine_values


class ROIPilotTests(unittest.TestCase):
    def test_union_retains_all_positive_codes_without_class_specific_rules(self):
        seg = np.zeros((5, 5, 5));seg[1, 1, 1] = 1;seg[3, 3, 3] = 4
        r = region_union(seg)
        self.assertEqual(r.sum(), 2)
        self.assertTrue(r[1, 1, 1] and r[3, 3, 3])
        for bad in [np.zeros((5, 5, 5)), -np.ones((5, 5, 5)), np.full((5, 5, 5), .5), np.full((5, 5, 5), np.nan)]:
            with self.assertRaises(ValueError):region_union(bad)

    def test_normalization_is_per_image_and_positive_affine_invariant(self):
        a = np.arange(1, 126, dtype=float).reshape(5, 5, 5)
        p = percentile_parameters(a)
        b = 2*a+10;q = percentile_parameters(b)
        np.testing.assert_allclose(normalize_values(a, p), normalize_values(b, q), atol=1e-14)
        self.assertEqual(normalize_values(np.array([0, 1000]), p).tolist(), [0, 1])
        with self.assertRaises(ValueError):percentile_parameters(np.ones((5, 5, 5)))

    def test_fixed_bins_hand_calculated_endpoints_and_constant_rejection(self):
        b, low, high = fixed_bins(np.array([0, .5, 1]))
        self.assertEqual((low, high), (0, 1));self.assertEqual(b.tolist(), [1, 17, 32])
        with self.assertRaisesRegex(ValueError, 'constant'):fixed_bins(np.ones(4))
        b, _, _ = fixed_bins(np.array([.5]), minimum=0, maximum=1)
        self.assertEqual(b.tolist(), [17])

    def test_ROI_does_not_fit_normalizer_and_empty_erosion_is_missing(self):
        a = np.arange(1, 126).reshape(5, 5, 5)
        r = np.zeros(a.shape, dtype=bool);r[1:3, 1:3, 1:3] = True
        e = np.zeros(a.shape, dtype=bool)
        x = intensity_diagnostics(a, r, e)
        other = ~r;y = intensity_diagnostics(a, other, e)
        self.assertEqual((x['p01'], x['p99']), (y['p01'], y['p99']))
        self.assertIsNone(x['erosion_JS_distance'])
        self.assertFalse(x['erosion_histogram_success'])
        self.assertEqual(x['erosion_error'], 'empty_eroded_ROI')
        self.assertEqual(sum(x['bin_counts']), r.sum())
        self.assertAlmostEqual(sum(x['bin_probabilities']), 1)
        self.assertFalse(x['normalization_uses_ROI'] or x['normalization_uses_clinical_label'])

    def test_six_bindings_are_distinct_patients_and_class_balanced(self):
        d = sample_binding(ROOT)
        self.assertEqual((len(d), d.patient_id.nunique()), (6, 6))
        self.assertEqual(d.tumor_label.value_counts().to_dict(), {0: 3, 1: 3})

    def test_unclipped_scale_preserves_tail_values_and_FBN_order(self):
        x=np.array([0,20,40,60,80,100]);p=dict(p01=20,p99=80)
        v=affine_values(x,p)
        self.assertLess(v[0],0);self.assertGreater(v[-1],1)
        self.assertEqual(np.unique(v).size,np.unique(x).size)
        np.testing.assert_array_equal(fixed_bins(x)[0],fixed_bins(v)[0])
        self.assertLess(np.unique(normalize_values(x,p)).size,np.unique(v).size)


if __name__ == '__main__':unittest.main()
