"""Coordinate diagnostics only; no registration, interpolation or label changes."""
import itertools
import numpy as np


def corner_distance_mm(a,b,shape,plane=None):
    choices=[(0,int(n)-1) for n in shape]
    if plane is not None:choices[2]=(int(plane),)
    xyz=np.array(list(itertools.product(*choices)),float)
    h=np.column_stack([xyz,np.ones(len(xyz))])
    delta=((np.asarray(a)-np.asarray(b))@h.T).T[:,:3]
    return float(np.max(np.linalg.norm(delta,axis=1)))


def fov_fraction(world_points,affine,shape):
    p=np.asarray(world_points,float)
    if p.ndim!=2 or p.shape[1]!=3 or len(p)==0:raise ValueError('Nonempty Nx3 points required')
    vox=np.linalg.solve(affine,np.column_stack([p,np.ones(len(p))]).T).T[:,:3]
    inside=np.all((vox>=-.5)&(vox<np.asarray(shape)-.5),axis=1)
    return dict(target_voxels=len(p),coordinate_fov_inside_voxels=int(inside.sum()),
                coordinate_fov_fraction=float(inside.mean()))
