import sys
from pathlib import Path
import unittest
import numpy as np
import SimpleITK as sitk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rn_public.rigid_pilot import image_from_col_row_slice,transformed_fov_fraction,screen_candidate


class RigidPilotTests(unittest.TestCase):
    def test_better_roi_coverage_cannot_override_worse_metric(self):
        bad=screen_candidate(dict(negative_mi_before=-.2,negative_mi_after=-.1,
            foreground_fov_overlap_before=.9,foreground_fov_overlap_after=.95))
        self.assertEqual(bad['metric_screen_pass'],0);self.assertEqual(bad['applied_to_analysis'],0)
        good=screen_candidate(dict(negative_mi_before=-.2,negative_mi_after=-.3,
            foreground_fov_overlap_before=.9,foreground_fov_overlap_after=.9))
        self.assertEqual(good['metric_screen_pass'],1);self.assertEqual(good['clinical_alignment_accepted'],0)
    def test_array_axes_and_ras_to_lps_physical_coordinate(self):
        data=np.zeros((3,4,5));data[1,2,3]=7
        a=np.diag([2.,3.,4.,1.]);a[:3,3]=[10,20,30]
        im=image_from_col_row_slice(data,a)
        self.assertEqual(im.GetSize(),(3,4,5));self.assertEqual(im[1,2,3],7)
        np.testing.assert_allclose(im.TransformIndexToPhysicalPoint((1,2,3)),[-12,-26,42])

    def test_fixed_to_moving_transform_direction_for_resampling(self):
        moving=sitk.Image([6,3,3],sitk.sitkFloat32);moving[3,1,1]=9
        reference=sitk.Image([6,3,3],sitk.sitkFloat32)
        tx=sitk.TranslationTransform(3,[1,0,0])
        output=sitk.Resample(moving,reference,tx,sitk.sitkNearestNeighbor)
        self.assertEqual(output[2,1,1],9)
        # LPS +1 maps RAS x=0 to RAS x=-1, outside a unit grid at origin.
        self.assertEqual(transformed_fov_fraction([[0,0,0]],tx,np.eye(4),(3,3,3)),0)
