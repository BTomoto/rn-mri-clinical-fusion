"""Review twelve mask-grid differences and inventory paired FLAIR geometry."""
from pathlib import Path
import gzip
import hashlib
import json
import sys
import zipfile
import nibabel as nib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.pair_geometry import corner_distance_mm,fov_fraction
from rn_public.imaging_qc import grid_alignment


def run():
    m=pd.read_csv(ROOT/'data/processed/cohort_baseline_mask_alignment.csv',dtype={'patient_id':str,'study_date_code':str})
    t1=pd.read_csv(ROOT/'data/processed/cohort_dicom_series_qc.csv',dtype={'patient_id':str,'study_date_code':str})
    files=pd.read_csv(ROOT/'data/processed/cohort_dicom_file_qc.csv.gz',dtype={'patient_id':str,'study_date_code':str},keep_default_na=False)
    fs=pd.read_csv(ROOT/'data/processed/flair_dicom_series_qc.csv',dtype={'patient_id':str,'study_date_code':str})
    ff=pd.read_csv(ROOT/'data/processed/flair_dicom_file_qc.csv.gz',dtype={'patient_id':str,'study_date_code':str},keep_default_na=False)
    inventory=pd.read_csv(ROOT/'data/processed/mask_file_audit.csv',dtype=str)
    precision=[];pairs=[]
    with zipfile.ZipFile(ROOT/'data/raw/openbtai/NIFTIs_Masks.zip') as z:
        names={Path(n).name:n for n in z.namelist() if n.endswith('.nii') and '__MACOSX' not in n}
        for r in m.itertuples():
            raw=z.read(names[r.mask_file]);digest=hashlib.sha256(raw).hexdigest()
            expected=inventory[inventory.mask_file==r.mask_file]
            if len(expected)!=1 or digest!=expected.iloc[0].sha256:raise ValueError('Mask SHA mismatch')
            mask=nib.Nifti1Image.from_bytes(raw);native=t1[t1.series_uid==r.series_uid].iloc[0]
            dicom_affine=np.array(json.loads(native.affine_ras_json));shape=tuple(map(int,native.volume_shape_col_row_slice.split('x')))
            if not r.grid_equivalent:
                trans=np.linalg.solve(dicom_affine,mask.affine);integer=np.rint(trans);ideal=dicom_affine@integer
                q=mask.get_qform();s=mask.get_sform()
                qalign=grid_alignment(mask.shape,q,shape,dicom_affine)
                group=files[files.SeriesInstanceUID==r.series_uid]
                pos=np.array([json.loads(x) for x in group.ImagePositionPatient])
                orient=np.array(json.loads(group.iloc[0].ImageOrientationPatient));normal=np.cross(orient[:3],orient[3:]);pos=pos[np.argsort(pos@normal)]
                local_first=float(np.linalg.norm(pos[1]-pos[0]));local_last=float(np.linalg.norm(pos[-1]-pos[-2]))
                nifti_step=float(np.linalg.norm(mask.affine[:3,2]));global_step=float(np.linalg.norm(dicom_affine[:3,2]))
                first=corner_distance_mm(mask.affine,ideal,mask.shape,plane=0)
                last=corner_distance_mm(mask.affine,ideal,mask.shape,plane=mask.shape[2]-1)
                precision.append(dict(lesion_key=r.lesion_key,patient_id=r.patient_id,study_date_code=r.study_date_code,
                    mask_file=r.mask_file,mask_sha256=digest,qform_code=int(mask.header['qform_code']),sform_code=int(mask.header['sform_code']),
                    qform_sform_corner_difference_mm=corner_distance_mm(q,s,mask.shape),
                    sform_dicom_corner_difference_mm=corner_distance_mm(s,ideal,mask.shape),
                    qform_dicom_corner_difference_mm=qalign['max_corner_error_mm'],qform_grid_equivalent=qalign['grid_equivalent'],
                    first_plane_corner_difference_mm=first,last_plane_corner_difference_mm=last,
                    closer_anchor='first_plane' if first<last else 'last_plane',nifti_slice_step_mm=nifti_step,
                    dicom_endpoint_slice_step_mm=global_step,dicom_first_pair_step_mm=local_first,dicom_last_pair_step_mm=local_last,
                    nearest_end_pair_step_difference_mm=min(abs(nifti_step-local_first),abs(nifti_step-local_last)),
                    original_grid_equivalent=0,review_resolved=0,source_header_changed=0,resampling_performed=0,
                    interpretation='conversion_or_coordinate_precision_pattern_only; exact_cause_unverified'))
            candidates=fs[(fs.patient_id==r.patient_id)&(fs.study_date_code==r.study_date_code)]
            if not len(candidates):
                pairs.append(dict(lesion_key=r.lesion_key,patient_id=r.patient_id,study_date_code=r.study_date_code,
                    flair_candidate_found=0,pair_status='no_named_flair_in_public_study',registration_performed=0,use_for_model=0))
                continue
            arr=np.asanyarray(mask.dataobj);coords=np.argwhere((arr//10)==int(r.lesion_key.split('_L')[1]))
            world=(mask.affine[:3,:3]@coords.T).T+mask.affine[:3,3]
            for c in candidates.itertuples():
                row=dict(lesion_key=r.lesion_key,patient_id=r.patient_id,study_date_code=r.study_date_code,
                    flair_candidate_found=1,flair_series_name=c.series_name,flair_series_uid=c.series_uid,
                    flair_files=int(c.files),flair_technical_stack_pass=int(c.technical_stack_pass),
                    flair_slice_step_mm=c.slice_step_mm,flair_slice_thickness_mm=float(c.SliceThickness),
                    flair_interslice_gap_present=int(c.interslice_gap_present),
                    postcontrast_name_hint=int(any(x in c.series_name.upper() for x in ['GADO','GD','GAD'])),
                    t1_mask_grid_equivalent=int(r.grid_equivalent),pair_status='header_geometry_candidate_only',
                    registration_performed=0,anatomical_pair_review_complete=0,use_for_model=0)
                native_files=files[files.SeriesInstanceUID==r.series_uid];flair_files=ff[ff.SeriesInstanceUID==c.series_uid]
                for tag in ['StudyInstanceUID','FrameOfReferenceUID']:
                    u=set(native_files[tag])-{''};v=set(flair_files[tag])-{''}
                    row[tag+'_comparison']='identical_single_uid' if len(u)==len(v)==1 and u==v else 'different_or_multiple_uids' if u and v else 'missing_uid'
                if c.geometry_regular:
                    row.update(fov_fraction(world,np.array(json.loads(c.affine_ras_json)),tuple(map(int,c.volume_shape_col_row_slice.split('x')))))
                pairs.append(row)
    p=pd.DataFrame(precision);a=pd.DataFrame(pairs)
    p.to_csv(ROOT/'data/processed/grid_precision_review.csv',index=False)
    a.to_csv(ROOT/'data/processed/baseline_flair_pairs.csv',index=False)
    paired=a[a.flair_candidate_found==1]
    summary=dict(grid_review_lesions=len(p),grid_review_unique_masks=int(p.mask_file.nunique()),
        qform_alone_resolves_grid_discrepancy=int(p.qform_grid_equivalent.sum()),
        max_qform_sform_corner_difference_mm=float(p.qform_sform_corner_difference_mm.max()),
        max_sform_dicom_corner_difference_mm=float(p.sform_dicom_corner_difference_mm.max()),
        closer_last_plane=int((p.closer_anchor=='last_plane').sum()),closer_first_plane=int((p.closer_anchor=='first_plane').sum()),
        resolved_grid_reviews=0,unchanged_strict_grid_equivalent_lesions=int(m.grid_equivalent.sum()),
        baseline_lesions=len(m),baseline_studies=int(m[['patient_id','study_date_code']].drop_duplicates().shape[0]),
        lesions_with_named_flair=int(paired.lesion_key.nunique()),lesions_without_named_flair=int(a[a.flair_candidate_found==0].lesion_key.nunique()),
        flair_series=int(fs.series_uid.nunique()),flair_files=int(fs.files.sum()),
        studies_with_named_flair=int(paired[['patient_id','study_date_code']].drop_duplicates().shape[0]),
        paired_all_target_centers_inside_coordinate_fov=int(paired.coordinate_fov_fraction.eq(1).sum()),
        paired_partial_coordinate_fov=int((paired.coordinate_fov_fraction<1).sum()),
        frame_uid_comparison_counts=paired.FrameOfReferenceUID_comparison.value_counts().to_dict(),
        fov_interpretation='coordinate extent only; not anatomical alignment, slice-gap coverage or validated registration',
        registration_performed=False,source_headers_changed=False,labels_changed=False,models_fitted=False,
        input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            ROOT/'data/processed/cohort_baseline_mask_alignment.csv',ROOT/'data/processed/flair_dicom_series_qc.csv',
            ROOT/'data/metadata/baseline_qc/flair_series_members.jsonl.gz']})
    (ROOT/'reports/grid_precision_and_flair_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(json.dumps(summary,indent=2),flush=True)
    return summary


if __name__=='__main__':run()
