import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rn_public.pair_geometry import corner_distance_mm,fov_fraction


class PairGeometryTests(unittest.TestCase):
    def test_corner_drift_includes_extent_and_physical_units(self):
        a=np.eye(4);b=np.eye(4);b[2,2]=1.01
        self.assertAlmostEqual(corner_distance_mm(a,b,(10,10,101)),1)
        self.assertEqual(corner_distance_mm(a,b,(10,10,101),plane=0),0)
        self.assertAlmostEqual(corner_distance_mm(a,b,(10,10,101),plane=100),1)

    def test_fraction_in_world_coordinates_and_half_open_edges(self):
        a=np.diag([2,3,4,1]);a[:3,3]=[10,20,30]
        vox=np.array([[0,0,0],[1.49,0,0],[1.5,0,0],[-.5,0,0],[-.5001,0,0]])
        world=(a[:3,:3]@vox.T).T+a[:3,3]
        result=fov_fraction(world,a,(2,2,2))
        self.assertEqual(result['coordinate_fov_inside_voxels'],3)
        self.assertAlmostEqual(result['coordinate_fov_fraction'],.6)
        with self.assertRaises(ValueError):fov_fraction([],a,(2,2,2))
