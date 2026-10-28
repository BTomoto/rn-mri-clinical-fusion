"""Conservative single-frame DICOM geometry checks; never adjudicate RN."""
import itertools
import re
import numpy as np


def resolve_series_name(mask_name, available):
    """Resolve only exact names or unique punctuation/case variants.

    Preserve both names; numerical grid checks must independently verify mapping.
    Never choose a fuzzy match or one of several normalized candidates.
    """
    available=set(available)
    if mask_name in available:return mask_name,'exact'
    canonical=lambda name:re.sub(r'[^a-z0-9]','',name.casefold())
    choices=[name for name in available if canonical(name)==canonical(mask_name)]
    if len(choices)!=1:raise ValueError(f'Unresolved or ambiguous series name: {mask_name}: {choices}')
    return choices[0],'unique_punctuation_case_variant'


def stack_geometry(positions, orientations, spacings, shape):
    """Return col,row,slice -> RAS affine only for a regular, unique stack.

    Numeric tolerances are engineering audit choices, not clinical QC criteria.
    Sorting uses plane position, never file name or InstanceNumber. SliceThickness
    does not determine the slice increment. In-plane slice shifts are retained.
    """
    p, o, s = (np.asarray(x, dtype=float) for x in (positions, orientations, spacings))
    result = dict(geometry_regular=0, reason='', slice_count=len(p))
    if len(p) < 2:
        result['reason'] = 'fewer_than_two_planes'
        return result
    if p.shape != (len(p), 3) or o.shape != (len(p), 6) or s.shape != (len(p), 2):
        result['reason'] = 'missing_geometry'
        return result
    if not all(np.isfinite(x).all() for x in (p, o, s)) or (s <= 0).any():
        result['reason'] = 'invalid_geometry'
        return result
    u, v = o[0, :3], o[0, 3:]
    if max(abs(np.linalg.norm(u)-1), abs(np.linalg.norm(v)-1), abs(u@v)) > 1e-4:
        result['reason'] = 'invalid_direction_cosines'
        return result
    if np.max(np.abs(o-o[0])) > 1e-4 or np.max(np.abs(s-s[0])) > 1e-4:
        result['reason'] = 'variable_orientation_or_pixel_spacing'
        return result
    normal = np.cross(u, v); normal /= np.linalg.norm(normal)
    order = np.argsort(p@normal, kind='stable'); p = p[order]
    gaps = np.diff(p@normal)
    step = float(np.median(gaps))
    result.update(duplicate_plane_count=int((gaps <= 1e-3).sum()),
                  slice_step_mm=step, gap_min_mm=float(gaps.min()), gap_max_mm=float(gaps.max()))
    if result['duplicate_plane_count']:
        result['reason'] = 'repeated_planes_do_not_stack'
        return result
    # NiBabel's multi-slice affine: the first and last plane anchor the volume.
    # A median incremental vector can accumulate scanner rounding errors.
    delta = (p[-1]-p[0])/(len(p)-1)
    residual = float(np.max(np.linalg.norm(p-(p[0]+np.arange(len(p))[:, None]*delta), axis=1)))
    result.update(max_step_deviation_mm=float(np.max(np.abs(gaps-step))),
                  affine_position_residual_mm=residual)
    if np.max(np.abs(gaps-step)) > max(.05, step*.01) or residual > .1:
        result['reason'] = 'irregular_plane_positions'
        return result
    a = np.eye(4)
    a[:3, 0] = u*s[0, 1]  # pixel_array columns
    a[:3, 1] = v*s[0, 0]  # pixel_array rows
    a[:3, 2] = delta
    a[:3, 3] = p[0]
    a = np.diag([-1., -1., 1., 1.])@a  # DICOM LPS -> NIfTI RAS
    result.update(geometry_regular=1, reason='regular_stack', affine_ras=a,
                  affine_step_estimator='first_last_position_difference_over_intervals',
                  order=order, volume_shape=(int(shape[1]), int(shape[0]), len(p)))
    return result


def grid_alignment(mask_shape, mask_affine, image_shape, image_affine, tolerance_voxels=1e-3):
    """Test complete-grid equivalence under axis permutation/flips, no resampling.

    Checking matrix elements alone can miss accumulated subvoxel drift. All eight
    volume corners must map within tolerance to the expected integer grid.
    """
    t = np.linalg.solve(image_affine, mask_affine)
    rounded = np.rint(t)
    rotation = rounded[:3, :3]
    signed_permutation = (np.isin(rotation, [-1, 0, 1]).all()
                          and np.all(np.sum(abs(rotation), axis=0) == 1)
                          and np.all(np.sum(abs(rotation), axis=1) == 1))
    corners = np.array(list(itertools.product(*[(0, int(n)-1) for n in mask_shape])))
    homogeneous = np.column_stack([corners, np.ones(8)])
    mapped = (t@homogeneous.T).T[:, :3]
    exact = (rounded@homogeneous.T).T[:, :3]
    error = float(np.max(abs(mapped-exact)))
    error_mm=float(np.max(np.linalg.norm((image_affine[:3,:3]@(mapped-exact).T).T,axis=1)))
    covers_grid = (np.array_equal(exact.min(axis=0), np.zeros(3))
                   and np.array_equal(exact.max(axis=0), np.asarray(image_shape)-1))
    ok = bool(signed_permutation and covers_grid and error <= tolerance_voxels)
    return dict(grid_equivalent=int(ok), max_corner_error_voxels=error,
                max_corner_error_mm=error_mm,
                signed_permutation_and_extent_match=int(signed_permutation and covers_grid),
                tolerance_voxels=tolerance_voxels, mask_to_image_voxel_transform=t.tolist(),
                integer_reindex_transform=rounded.astype(int).tolist() if ok else None,
                interpolation_performed=False, registration_performed=False)


def sequence_hints(name, description, image_type):
    """Names are candidates only; T1 FLAIR is not a T2-FLAIR candidate."""
    text = (name+' '+description).upper()
    t1_flair = 'FLAIR' in text and 'T1' in text
    return dict(t2_flair_metadata_candidate=int('FLAIR' in text and not t1_flair),
                t1_flair_name=int(t1_flair),
                t1_3d_metadata_candidate=int('T1' in text and any(x in text for x in ['3D', 'TFE'])),
                contrast_name_hint=int(any(x in text for x in ['GD', 'GADO', 'GAD', 'C+'])),
                derived_or_projection_hint=int(any(x in str(image_type).upper()
                                                  for x in ['DERIVED', 'MPR', 'PROJECTION'])),
                contrast_administration_verified=0)
