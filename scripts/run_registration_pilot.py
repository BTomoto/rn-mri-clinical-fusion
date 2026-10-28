"""Run three prespecified rigid T1/FLAIR trials; never set model eligibility."""
from pathlib import Path
import gc
import gzip
import hashlib
import json
import sys
import zipfile
import numpy as np
import pandas as pd
import pydicom
import nibabel as nib
import SimpleITK as sitk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.imaging_qc import stack_geometry
from rn_public.rigid_pilot import image_from_col_row_slice,normalize_for_registration,isotropic_reference,fit_rigid,transformed_fov_fraction,screen_candidate

CASES={'10005_L1':'conventional_thick_slice_flair','10029_L2':'three_dimensional_flair','40158_L1':'known_coordinate_fov_boundary'}


def restore_pilot():
    keys=set()
    align=pd.read_csv(ROOT/'data/processed/cohort_baseline_mask_alignment.csv',dtype={'patient_id':str,'study_date_code':str})
    for r in align[align.lesion_key.isin(CASES)].itertuples():keys.add((r.patient_id,r.study_date_code))
    entries=[]
    for name in ['mask_series_members.jsonl.gz','flair_series_members.jsonl.gz']:
        rows=map(json.loads,gzip.decompress((ROOT/'data/metadata/baseline_qc'/name).read_bytes()).decode().splitlines())
        entries.extend(e for e in rows if (e['patient_id'],e['study_date_code']) in keys)
    wanted={e['member']:e for e in entries};verified=[]
    for part in json.loads((ROOT/'data/metadata/imaging_archive_parts.json').read_text()):
        path=ROOT/'dist/restored_mri'/part['filename']
        if not path.is_file():continue
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=part['sha256']:raise ValueError('Archive SHA mismatch')
        verified.append(dict(filename=part['filename'],sha256=digest))
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                name=info.filename.removeprefix('data/imaging/dicom/')
                if name not in wanted:continue
                p=ROOT/'data/imaging/dicom'/name
                if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==wanted[name]['sha256']:continue
                raw=z.read(info)
                if hashlib.sha256(raw).hexdigest()!=wanted[name]['sha256']:raise ValueError('Archive member SHA mismatch')
                p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    out=ROOT/'data/metadata/registration_pilot';out.mkdir(exist_ok=True)
    for e in entries:
        e['path']='data/imaging/dicom/'+e['member']
        p=ROOT/e['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:
            raise FileNotFoundError('Restore pilot source MRI or run original source restoration scripts: '+e['member'])
    raw=''.join(json.dumps(e)+'\n' for e in sorted(entries,key=lambda e:e['member'])).encode()
    (out/'selected_members.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    return entries,verified


def load_series(entries,series_name,pid,date):
    records=[e for e in entries if e['patient_id']==pid and e['study_date_code']==date and Path(e['member']).parent.name==series_name]
    ds=[pydicom.dcmread(ROOT/e['path']) for e in records]
    if not ds or len({str(d.SeriesInstanceUID) for d in ds})!=1:raise ValueError('Missing or mixed series')
    g=stack_geometry([d.ImagePositionPatient for d in ds],[d.ImageOrientationPatient for d in ds],
        [d.PixelSpacing for d in ds],(int(ds[0].Rows),int(ds[0].Columns)))
    if not g['geometry_regular']:raise ValueError(g['reason'])
    vol=np.stack([ds[i].pixel_array.astype(np.float32)*float(getattr(ds[i],'RescaleSlope',1))+float(getattr(ds[i],'RescaleIntercept',0)) for i in g['order']],axis=-1).transpose(1,0,2)
    return image_from_col_row_slice(vol,g['affine_ras']),g


def review_figure(fixed,moving,tx,center_ras,path,title):
    reference=isotropic_reference(fixed,2.)
    f=sitk.Resample(normalize_for_registration(fixed),reference,sitk.Transform(3,sitk.sitkIdentity),sitk.sitkLinear,0.)
    before=sitk.Resample(normalize_for_registration(moving),reference,sitk.Transform(3,sitk.sitkIdentity),sitk.sitkLinear,0.)
    after=sitk.Resample(normalize_for_registration(moving),reference,tx,sitk.sitkLinear,0.)
    v=np.array(reference.TransformPhysicalPointToContinuousIndex(tuple(center_ras*np.array([-1,-1,1]))))
    k=int(np.clip(np.rint(v[2]),0,reference.GetSize()[2]-1))
    arrays=[sitk.GetArrayFromImage(x)[k] for x in [f,before,after]]
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    axes[0].imshow(arrays[0],cmap='gray',vmin=0,vmax=1,origin='lower');axes[0].set_title('T1 fixed 2mm display grid')
    for ax,a,label in zip(axes[1:],arrays[1:],['Header alignment','Rigid trial']):
        ax.imshow(np.clip(np.stack([arrays[0],a,np.zeros_like(a)],axis=-1),0,1),origin='lower')
        ax.set_title(label+' | red T1, green FLAIR')
    for ax in axes:ax.set_axis_off()
    fig.suptitle(title+' | technical overlay, clinical acceptance pending',fontsize=10)
    fig.tight_layout();fig.savefig(path,dpi=130);plt.close(fig)


def run(repeat_first=True):
    entries,parts=restore_pilot();out=ROOT/'outputs/registration-pilot-20261029';out.mkdir(exist_ok=True,parents=True)
    align=pd.read_csv(ROOT/'data/processed/cohort_baseline_mask_alignment.csv',dtype={'patient_id':str,'study_date_code':str})
    pairs=pd.read_csv(ROOT/'data/processed/baseline_flair_pairs.csv',dtype={'patient_id':str,'study_date_code':str})
    records=[];detail=[]
    with zipfile.ZipFile(ROOT/'data/raw/openbtai/NIFTIs_Masks.zip') as z:
        for index,(key,reason) in enumerate(CASES.items()):
            print('Rigid pilot',key,reason,flush=True)
            r=align[align.lesion_key==key].iloc[0];p=pairs[pairs.lesion_key==key].iloc[0]
            if r.grid_equivalent!=1:raise ValueError('Pilot requires unchanged sform-grid equivalence')
            fixed,fg=load_series(entries,r.dicom_series_name,r.patient_id,r.study_date_code)
            moving,mg=load_series(entries,p.flair_series_name,r.patient_id,r.study_date_code)
            tx,metrics=fit_rigid(fixed,moving)
            metrics.update(screen_candidate(metrics))
            trace=metrics.pop('iteration_trace')
            sitk.WriteTransform(tx,str(out/(key+'_candidate_fixed_to_moving.tfm')))
            mask_name=next(n for n in z.namelist() if Path(n).name==r.mask_file and '__MACOSX' not in n)
            mask_bytes=z.read(mask_name)
            if hashlib.sha256(mask_bytes).hexdigest()!=r.mask_sha256:raise ValueError('Pilot mask SHA mismatch')
            mask=nib.Nifti1Image.from_bytes(mask_bytes);arr=np.asanyarray(mask.dataobj)
            coords=np.argwhere((arr//10)==int(key.split('_L')[1]));world=(mask.affine[:3,:3]@coords.T).T+mask.affine[:3,3]
            identity=sitk.Transform(3,sitk.sitkIdentity)
            metrics.update(target_coordinate_fov_before=transformed_fov_fraction(world,identity,mg['affine_ras'],mg['volume_shape']),
                target_coordinate_fov_after=transformed_fov_fraction(world,tx,mg['affine_ras'],mg['volume_shape']))
            if index==0 and repeat_first:
                again,_=fit_rigid(fixed,moving)
                metrics['repeat_max_parameter_difference']=float(np.max(abs(np.array(tx.GetParameters())-np.array(again.GetParameters()))))
            review_figure(fixed,moving,tx,world.mean(0),out/(key+'_registration_review.png'),key)
            detail.append(dict(lesion_key=key,selection_reason=reason,metrics=metrics,iteration_trace=trace,
                transform_direction='fixed T1 LPS physical point to moving FLAIR LPS physical point'))
            records.append(dict(lesion_key=key,selection_reason=reason,negative_mi_before=metrics['negative_mi_before'],
                negative_mi_after=metrics['negative_mi_after'],metric_improved=int(metrics['metric_improved']),
                translation_norm_mm=float(np.linalg.norm(metrics['translation_mm'])),max_abs_rotation_degrees=float(np.max(abs(np.array(metrics['rotations_degrees'])))),
                foreground_fov_overlap_before=metrics['foreground_fov_overlap_before'],foreground_fov_overlap_after=metrics['foreground_fov_overlap_after'],
                target_coordinate_fov_before=metrics['target_coordinate_fov_before'],target_coordinate_fov_after=metrics['target_coordinate_fov_after'],
                optimizer_stop=metrics['optimizer_stop'],clinical_alignment_accepted=0,use_for_model=0))
            records[-1].update(screen_candidate(metrics))
            del fixed,moving,mask,arr;gc.collect()
    pd.DataFrame(records).to_csv(ROOT/'data/processed/registration_pilot.csv',index=False)
    summary=dict(cases=detail,case_count=len(records),verified_source_files=len(entries),verified_source_bytes=sum(e['size_bytes'] for e in entries),
        restored_archive_parts=parts,method=dict(library='SimpleITK',version=sitk.Version_VersionString(),transform='Euler3D rigid',
            initialization='identity parameters; rotation center fixed-image physical center',histogram_bins=50,
            sampling='random 20 percent, seed 20261029',threads=1,registration_grid_mm=2.,evaluation_grid_mm=3.,
            pyramid_shrink=[4,2,1],pyramid_smoothing_mm=[2,1,0],iteration_limit_per_level=200,
            optimizer='RegularStepGradientDescent',learning_rate=.5,min_step=.005,relaxation_factor=.5,
            foreground='normalized fixed intensity >0.05; not a validated brain mask',interpolator='linear',
            engineering_screen='negative MI improves and foreground overlap loss <=0.02; not clinical validation',
            objective='negative Mattes mutual information; lower is better'),
        clinical_alignment_accepted=0,source_images_or_masks_overwritten=False,prediction_model_fitted=False,
        derived_resampling_performed=True,scope='three method trials only; not all 46 paired lesions',
        metrics_are_not_clinical_validation=True)
    (ROOT/'reports/registration_pilot.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(pd.DataFrame(records).to_string(index=False),flush=True)
    return summary


if __name__=='__main__':run()
