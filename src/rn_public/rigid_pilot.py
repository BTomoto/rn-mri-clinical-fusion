"""Rigid T1/FLAIR method pilot; metrics never adjudicate clinical alignment."""
import numpy as np
import SimpleITK as sitk


def image_from_col_row_slice(volume,affine_ras):
    a=np.diag([-1.,-1.,1.,1.])@np.asarray(affine_ras,float)
    spacing=np.linalg.norm(a[:3,:3],axis=0)
    im=sitk.GetImageFromArray(np.transpose(volume,(2,1,0)).astype(np.float32))
    im.SetSpacing(tuple(spacing));im.SetDirection(tuple((a[:3,:3]/spacing).ravel()))
    im.SetOrigin(tuple(a[:3,3]));return im


def normalize_for_registration(im):
    arr=sitk.GetArrayFromImage(im);positive=arr[arr>0]
    if len(positive)==0:raise ValueError('No positive image intensities')
    low,high=np.percentile(positive,[1,99])
    if high<=low:raise ValueError('Constant image')
    out=sitk.GetImageFromArray(np.clip((arr-low)/(high-low),0,1).astype(np.float32))
    out.CopyInformation(im);return out


def isotropic_reference(im,spacing=2.):
    size=np.ceil((np.array(im.GetSize())-1)*np.array(im.GetSpacing())/spacing).astype(int)+1
    ref=sitk.Image([int(x) for x in size],sitk.sitkFloat32)
    ref.SetOrigin(im.GetOrigin());ref.SetDirection(im.GetDirection());ref.SetSpacing([spacing]*3)
    return ref


def transformed_fov_fraction(points_ras,transform,moving_affine_ras,moving_shape):
    points=np.asarray(points_ras,float)
    lps=points*np.array([-1,-1,1])
    mapped=np.array([transform.TransformPoint(tuple(p)) for p in lps])*np.array([-1,-1,1])
    vox=np.linalg.solve(moving_affine_ras,np.c_[mapped,np.ones(len(mapped))].T).T[:,:3]
    return float(np.all((vox>=-.5)&(vox<np.array(moving_shape)-.5),axis=1).mean())


def fit_rigid(fixed,moving,seed=20261029,optimizer='regular_step'):
    """Transform maps fixed physical LPS points to moving physical LPS points."""
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    f=normalize_for_registration(fixed);m=normalize_for_registration(moving)
    ref=isotropic_reference(f,2.)
    f=sitk.Resample(f,ref,sitk.Transform(3,sitk.sitkIdentity),sitk.sitkLinear,0.)
    # This is an intensity foreground mask, not skull stripping or brain segmentation.
    foreground=sitk.Cast(f>.05,sitk.sitkUInt8)
    initial=sitk.Euler3DTransform()
    initial.SetCenter(f.TransformContinuousIndexToPhysicalPoint(tuple((np.array(f.GetSize())-1)/2)))
    method=sitk.ImageRegistrationMethod();method.SetMetricAsMattesMutualInformation(50)
    method.SetMetricSamplingStrategy(method.RANDOM);method.SetMetricSamplingPercentage(.2,seed)
    method.SetMetricFixedMask(foreground);method.SetInterpolator(sitk.sitkLinear)
    if optimizer=='initial_gradient_descent':
        method.SetOptimizerAsGradientDescent(learningRate=1.,numberOfIterations=100,
            convergenceMinimumValue=1e-6,convergenceWindowSize=10)
    elif optimizer=='regular_step':
        method.SetOptimizerAsRegularStepGradientDescent(learningRate=.5,minStep=.005,
            numberOfIterations=200,relaxationFactor=.5,gradientMagnitudeTolerance=1e-8)
    else:raise ValueError('Unknown prespecified optimizer')
    method.SetOptimizerScalesFromPhysicalShift()
    method.SetShrinkFactorsPerLevel([4,2,1]);method.SetSmoothingSigmasPerLevel([2,1,0]);method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    method.SetInitialTransform(initial,inPlace=False)
    trace=[]
    method.AddCommand(sitk.sitkIterationEvent,lambda:trace.append(dict(level=int(method.GetCurrentLevel()),iteration=int(method.GetOptimizerIteration()),negative_mi=float(method.GetMetricValue()))))
    transform=method.Execute(f,m)
    # Common full 3mm grid and fixed foreground for both pre/post evaluations.
    eval_fixed=sitk.Resample(f,isotropic_reference(f,3.),sitk.Transform(3,sitk.sitkIdentity),sitk.sitkLinear,0.)
    eval_mask=sitk.Cast(eval_fixed>.05,sitk.sitkUInt8)
    def evaluate(tx):
        metric=sitk.ImageRegistrationMethod();metric.SetMetricAsMattesMutualInformation(50)
        metric.SetMetricFixedMask(eval_mask);metric.SetInterpolator(sitk.sitkLinear);metric.SetInitialTransform(tx)
        value=float(metric.MetricEvaluate(eval_fixed,m))
        ids=np.argwhere(sitk.GetArrayFromImage(eval_mask)>0)[:,::-1]
        direction=np.array(eval_fixed.GetDirection()).reshape(3,3)
        world=(direction@(ids*np.array(eval_fixed.GetSpacing())).T).T+eval_fixed.GetOrigin()
        inverse_direction=np.linalg.inv(np.array(m.GetDirection()).reshape(3,3))
        mapped=np.array([tx.TransformPoint(tuple(p)) for p in world])
        vox=(inverse_direction@(mapped-np.array(m.GetOrigin())).T).T/np.array(m.GetSpacing())
        overlap=float(np.all((vox>=-.5)&(vox<np.array(m.GetSize())-.5),axis=1).mean())
        return value,overlap
    before,overlap_before=evaluate(initial);after,overlap_after=evaluate(transform)
    euler=sitk.Euler3DTransform(sitk.CompositeTransform(transform).GetBackTransform())
    return transform,dict(negative_mi_before=before,negative_mi_after=after,
        negative_mi_change=after-before,foreground_fov_overlap_before=overlap_before,foreground_fov_overlap_after=overlap_after,
        rotations_degrees=np.degrees(euler.GetParameters()[:3]).tolist(),translation_mm=list(euler.GetTranslation()),
        optimizer_stop=method.GetOptimizerStopConditionDescription(),iteration_trace=trace,
        metric_improved=bool(after<before),anatomical_review_complete=False,clinical_alignment_accepted=False)


def screen_candidate(metrics):
    """Engineering triage only; the 2 percentage-point overlap loss is not clinical validation."""
    passed=bool(metrics['negative_mi_after']<metrics['negative_mi_before'] and
        metrics['foreground_fov_overlap_after']>=metrics['foreground_fov_overlap_before']-.02)
    return dict(metric_screen_pass=int(passed),candidate_status='metric_screen_only_needs_anatomical_review' if passed else 'rejected_metric_or_overlap',
                applied_to_analysis=0,clinical_alignment_accepted=0)
