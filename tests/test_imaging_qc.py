import unittest
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rn_public.imaging_qc import stack_geometry, grid_alignment, sequence_hints, resolve_series_name


class ImagingQCTest(unittest.TestCase):
    def test_name_variants_require_unique_non_fuzzy_match(self):
        self.assertEqual(resolve_series_name('AXIAL_+C',['AXIAL_C','FLAIR']),('AXIAL_C','unique_punctuation_case_variant'))
        with self.assertRaises(ValueError):resolve_series_name('AXIAL_+C',['AXIAL_C','AXIAL-C'])
        with self.assertRaises(ValueError):resolve_series_name('AXIAL_+C',['AXIAL_PRE'])
    def geometry(self, positions):
        n=len(positions)
        return stack_geometry(positions, [[1,0,0,0,1,0]]*n, [[2,3]]*n, (7,9))

    def test_position_order_and_array_axes(self):
        g=self.geometry([[10,20,6],[10,20,0],[10,20,3]])
        self.assertEqual(g['geometry_regular'],1)
        np.testing.assert_array_equal(g['order'],[1,2,0])
        np.testing.assert_allclose(g['affine_ras'],[[-3,0,0,-10],[0,-2,0,-20],[0,0,3,0],[0,0,0,1]])
        self.assertEqual(g['volume_shape'],(9,7,3))

    def test_repeated_planes_and_missing_planes_rejected(self):
        self.assertEqual(self.geometry([[0,0,z] for z in [0,1,1,2]])['geometry_regular'],0)
        self.assertEqual(self.geometry([[0,0,z] for z in [0,1,2,4]])['geometry_regular'],0)

    def test_affine_anchors_last_plane_despite_increment_rounding(self):
        g=self.geometry([[0,0,z] for z in [0,1.0004,2.0001,3.0003]])
        self.assertEqual(g['geometry_regular'],1)
        self.assertAlmostEqual(g['affine_ras'][2,2],1.0001)
        self.assertAlmostEqual((g['affine_ras']@np.array([0,0,3,1]))[2],3.0003)

    def test_variable_orientation_rejected(self):
        g=stack_geometry([[0,0,0],[0,0,1]],[[1,0,0,0,1,0],[0,1,0,1,0,0]],[[1,1]]*2,(4,4))
        self.assertEqual(g['geometry_regular'],0)

    def test_flips_permutations_and_cumulative_drift(self):
        a=np.array([[-1,0,0,8],[0,-1,0,6],[0,0,1,0],[0,0,0,1]],float)
        self.assertEqual(grid_alignment((9,7,3),a,(9,7,3),np.eye(4))['grid_equivalent'],1)
        a[0,0]-=.0002
        self.assertEqual(grid_alignment((9,7,3),a,(9,7,3),np.eye(4))['grid_equivalent'],0)
        p=np.eye(4);p[:3,:3]=[[0,1,0],[1,0,0],[0,0,1]]
        self.assertEqual(grid_alignment((7,9,3),p,(9,7,3),np.eye(4))['grid_equivalent'],1)

    def test_wrong_extent_and_translation_rejected(self):
        a=np.eye(4);a[0,3]=1
        self.assertEqual(grid_alignment((9,7,3),a,(9,7,3),np.eye(4))['grid_equivalent'],0)
        self.assertEqual(grid_alignment((9,7,2),np.eye(4),(9,7,3),np.eye(4))['grid_equivalent'],0)

    def test_flair_t1_and_projection_not_promoted(self):
        x=sequence_hints('SAG_FLAIR_T1','','ORIGINAL')
        self.assertEqual(x['t2_flair_metadata_candidate'],0)
        self.assertEqual(sequence_hints('TRA_FLAIR_T2-GADO','','ORIGINAL')['t2_flair_metadata_candidate'],1)
        x=sequence_hints('TRA_GD','','ORIGINAL PRIMARY PROJECTION IMAG')
        self.assertEqual(x['derived_or_projection_hint'],1)
        self.assertEqual(x['contrast_administration_verified'],0)
