"""All-file technical QC of the four added baseline studies; no RN labels."""
from pathlib import Path
import collections
import gzip
import hashlib
import importlib.metadata
import json
import sys
import zipfile
import zlib
import numpy as np
import pandas as pd
import pydicom
import nibabel as nib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.imaging_qc import stack_geometry, grid_alignment, sequence_hints, resolve_series_name


def source_path(record):
    # Original addition staging or the common path used inside the durable ZIP.
    for p in [ROOT/record['path'], ROOT/'data/imaging/dicom'/record['member']]:
        if p.is_file():return p
    raise FileNotFoundError(f"Restore additional-baseline archive: {record['member']}")


def vector(d,tag,n):
    try:
        a=np.asarray(getattr(d,tag),float)
        return a.tolist() if a.shape==(n,) else [float('nan')]*n
    except (AttributeError,TypeError,ValueError):return [float('nan')]*n


def run(manifest_relative='data/metadata/endpoint_followup/additional_baseline_imaging.jsonl',
        prefix='additional', output_subdir='imaging-qc-20261028',
        scope='all files in four added baseline studies only',
        mask_candidates_only=False, write_overlays=True, include_mask_audit=True):
    manifest=ROOT/manifest_relative
    manifest_bytes=manifest.read_bytes() if manifest.is_file() else gzip.decompress(Path(str(manifest)+'.gz').read_bytes())
    entries=[json.loads(line) for line in manifest_bytes.decode().splitlines()]
    if len({e['member'] for e in entries})!=len(entries):raise ValueError('Duplicate source members')
    files=[];headers={};paths={}
    for e in entries:
        p=source_path(e);b=p.read_bytes()
        r=dict(patient_id=e['patient_id'],study_date_code=e['study_date_code'],archive_id=e['archive_id'],
               member=e['member'],series_directory=str(Path(e['member']).parent),
               source_sha256=e['sha256'],sha256_match=int(hashlib.sha256(b).hexdigest()==e['sha256']),
               size_match=int(len(b)==e['size_bytes']),crc32_match=int(zlib.crc32(b)==e['zip_crc32']),
               header_readable=0,pixel_decodable=0,error='')
        try:
            d=pydicom.dcmread(p);r['header_readable']=1
            for tag in ['SeriesInstanceUID','StudyInstanceUID','SOPInstanceUID','FrameOfReferenceUID',
                        'SeriesDescription','Modality','StudyDate','NumberOfFrames','Rows','Columns',
                        'SliceThickness','SpacingBetweenSlices','ContrastBolusAgent','EchoTime',
                        'RepetitionTime','InversionTime','InstanceNumber']:
                r[tag]=str(getattr(d,tag,''))
            r['ImageType']='\\'.join(map(str,getattr(d,'ImageType',[])))
            r['TransferSyntaxUID']=str(d.file_meta.TransferSyntaxUID)
            for tag,n in [('ImagePositionPatient',3),('ImageOrientationPatient',6),('PixelSpacing',2)]:
                r[tag]=json.dumps(vector(d,tag,n))
            r['study_date_matches_directory']=int(str(getattr(d,'StudyDate',''))==e['study_date_code'])
            a=d.pixel_array
            r.update(pixel_decodable=1,pixel_shape='x'.join(map(str,a.shape)),
                     pixel_finite=int(np.isfinite(a).all()),pixel_min=int(a.min()),pixel_max=int(a.max()),
                     constant_pixel_array=int(a.max()==a.min()),
                     single_frame_2d=int(a.ndim==2 and int(getattr(d,'NumberOfFrames',1))==1),
                     pixel_shape_matches_header=int(a.shape==(int(d.Rows),int(d.Columns))))
            d.PixelData=b''  # Release the pixel buffer; retain only small headers.
            headers[e['member']]=d;paths[e['member']]=p
        except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
        files.append(r)
    f=pd.DataFrame(files)
    sop_counts=f.loc[f.SOPInstanceUID.ne(''),'SOPInstanceUID'].value_counts()
    f['sop_uid_occurrences']=f.SOPInstanceUID.map(sop_counts).fillna(0).astype(int)
    groups=collections.defaultdict(list)
    for r in files:groups[(r['series_directory'],r.get('SeriesInstanceUID',''))].append(r)
    series=[];valid_stacks={}
    directory_uid_count=f.groupby('series_directory').SeriesInstanceUID.nunique()
    for (directory,uid),records in sorted(groups.items()):
        ds=[headers[r['member']] for r in records if r['member'] in headers]
        first=records[0];directory_name=Path(directory).name
        r=dict(patient_id=first['patient_id'],study_date_code=first['study_date_code'],
               series_directory=directory,series_name=directory_name,series_uid=uid,files=len(records),
               directory_series_uid_count=int(directory_uid_count[directory]),
               decoded_files=sum(x['pixel_decodable'] for x in records),
               integrity_ok_files=sum(x['sha256_match']*x['crc32_match']*x['size_match'] for x in records),
               constant_slices=sum(x.get('constant_pixel_array',0) for x in records),
               date_mismatch_files=sum(1-x.get('study_date_matches_directory',0) for x in records),
               duplicated_sop_files=sum(x['sop_uid_occurrences']>1 for x in f[f.member.isin([x['member'] for x in records])].to_dict('records')),
               geometry_regular=0,geometry_reason='unreadable_or_not_single_frame',
               anatomical_review_complete=0,use_for_model=0)
        for tag in ['SeriesDescription','ImageType','ContrastBolusAgent','EchoTime','RepetitionTime','InversionTime','SliceThickness','SpacingBetweenSlices']:
            r[tag]=first.get(tag,'')
        r.update(sequence_hints(directory_name,r['SeriesDescription'],r['ImageType']))
        if len(ds)==len(records) and all(x.get('single_frame_2d',0) for x in records):
            shapes={(int(d.Rows),int(d.Columns)) for d in ds}
            if len(shapes)==1:
                g=stack_geometry([vector(d,'ImagePositionPatient',3) for d in ds],
                                 [vector(d,'ImageOrientationPatient',6) for d in ds],
                                 [vector(d,'PixelSpacing',2) for d in ds],next(iter(shapes)))
                for k,v in g.items():
                    if k not in ['affine_ras','order','volume_shape','reason']:r[k]=v
                r['geometry_reason']=g['reason']
                if g['geometry_regular']:
                    r['volume_shape_col_row_slice']='x'.join(map(str,g['volume_shape']))
                    r['affine_ras_json']=json.dumps(g['affine_ras'].tolist())
                    valid_stacks[(directory,uid)]=(g,records)
            else:r['geometry_reason']='variable_matrix_size'
        if r['geometry_regular']:
            for tag,output_key in [('SpacingBetweenSlices','spacing_tag_position_mismatch'),('SliceThickness','interslice_gap_present')]:
                try:
                    recorded=float(r[tag]);actual=r['slice_step_mm']
                    r[output_key]=int(abs(actual-recorded)>max(.05,.01*actual)) if output_key=='spacing_tag_position_mismatch' else int(actual-recorded>max(.05,.01*actual))
                except ValueError:r[output_key]=None
        r['technical_stack_pass']=int(r['geometry_regular'] and r['decoded_files']==r['files']
            and r['integrity_ok_files']==r['files'] and r['directory_series_uid_count']==1
            and r['date_mismatch_files']==0 and r['duplicated_sop_files']==0
            and all(x.get('pixel_finite',0) and x.get('pixel_shape_matches_header',0) for x in records))
        series.append(r)
    s=pd.DataFrame(series)
    a=pd.read_csv(ROOT/'data/processed/followup_availability_current.csv',dtype={'patient_id':str,'baseline_study_date_code':str,'baseline_mask_date_code':str})
    if mask_candidates_only:
        a=a[a.baseline_mask_available==1].copy()
        a['baseline_study_date_code']=a.baseline_mask_date_code
    studies={(e['patient_id'],e['study_date_code']) for e in entries}
    candidates=a[[ (r.patient_id,r.baseline_study_date_code) in studies for r in a.itertuples() ]]
    if not include_mask_audit:candidates=a.iloc[:0]
    mask_records=[]
    output=ROOT/'outputs'/output_subdir;output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ROOT/'data/raw/openbtai/NIFTIs_Masks.zip') as z:
        for c in candidates.itertuples():
            r=dict(lesion_key=c.lesion_key,patient_id=c.patient_id,study_date_code=c.baseline_study_date_code,
                   baseline_mask_available=int(c.baseline_mask_available),mask_file=c.baseline_mask_file,
                   grid_equivalent=0,alignment_status='no_contemporaneous_baseline_mask',
                   anatomical_review_complete=0,use_for_model=0)
            if c.baseline_mask_available:
                name=str(c.baseline_mask_file);target=name.removeprefix(f'{c.patient_id}_{c.baseline_mask_date_code}_').removesuffix('_msk.nii')
                available=s[(s.patient_id==c.patient_id)&(s.study_date_code==c.baseline_mask_date_code)].series_name
                try:
                    resolved,rule=resolve_series_name(target,available)
                    r.update(mask_series_name=target,dicom_series_name=resolved,name_match_rule=rule)
                except ValueError:
                    resolved=None;r['name_match_rule']='unresolved_or_ambiguous'
                matching=[(k,g,recs) for k,(g,recs) in valid_stacks.items()
                          if recs[0]['patient_id']==c.patient_id and recs[0]['study_date_code']==c.baseline_mask_date_code and Path(k[0]).name==resolved]
                members=[n for n in z.namelist() if Path(n).name==name and '__MACOSX' not in n]
                if len(matching)!=1 or len(members)!=1:
                    r['alignment_status']='ambiguous_or_missing_matching_stack'
                else:
                    key,g,recs=matching[0];raw=z.read(members[0]);mask=nib.Nifti1Image.from_bytes(raw)
                    inventory=pd.read_csv(ROOT/'data/processed/mask_file_audit.csv',dtype=str)
                    prior=inventory[inventory.mask_file==name]
                    if len(prior)!=1 or hashlib.sha256(raw).hexdigest()!=prior.iloc[0].sha256:
                        raise ValueError('Mask bytes disagree with previous verified mask inventory')
                    align=grid_alignment(mask.shape,mask.affine,g['volume_shape'],g['affine_ras'])
                    r.update(align,mask_sha256=hashlib.sha256(raw).hexdigest(),series_uid=key[1],
                             series_directory=key[0],mask_shape='x'.join(map(str,mask.shape)),
                             qform_code=int(mask.header['qform_code']),sform_code=int(mask.header['sform_code']),
                             mask_affine_ras_json=json.dumps(mask.affine.tolist()),
                             alignment_status='grid_equivalent_no_interpolation' if align['grid_equivalent'] else 'grid_mismatch_requires_review')
                    labels=np.asanyarray(mask.dataobj);coords=np.argwhere((labels//10)==int(c.lesion_id))
                    r['target_voxels']=len(coords)
                    if len(coords):
                        t=np.asarray(align['mask_to_image_voxel_transform'])
                        continuous=(t[:3,:3]@coords.T).T+t[:3,3]
                        inside=np.all((continuous>=-.5)&(continuous<np.array(g['volume_shape'])-.5),axis=1)
                        r['target_voxels_inside_image_fov']=int(inside.sum())
                        nearest=np.rint(continuous).astype(int)
                        r['target_max_reindex_error_mm']=float(np.max(np.linalg.norm((g['affine_ras'][:3,:3]@(continuous-nearest).T).T,axis=1)))
                        constant=np.array([recs[i].get('constant_pixel_array',0) for i in g['order']])
                        valid=(nearest[:,2]>=0)&(nearest[:,2]<len(constant))
                        r['target_voxels_on_constant_slices']=int(constant[nearest[valid,2]].sum())
                    if align['grid_equivalent'] and len(coords):
                        t=np.asarray(align['integer_reindex_transform']);mapped=(t[:3,:3]@coords.T).T+t[:3,3]
                        r['target_voxels_inside_image']=int(np.all((mapped>=0)&(mapped<np.array(g['volume_shape'])),axis=1).sum())
                    if align['grid_equivalent'] and len(coords) and write_overlays:
                        ordered=[recs[i] for i in g['order']]
                        target_slices=np.unique(mapped[:,2]);chosen=target_slices[np.linspace(0,len(target_slices)-1,min(3,len(target_slices))).round().astype(int)]
                        fig,axes=plt.subplots(1,len(chosen),figsize=(4*len(chosen),4),squeeze=False)
                        for ax,k in zip(axes[0],chosen):
                            pixels=pydicom.dcmread(paths[ordered[int(k)]['member']]).pixel_array.T
                            low,high=np.percentile(pixels,[1,99.5]);ax.imshow(pixels.T,cmap='gray',vmin=low,vmax=high,origin='lower')
                            points=mapped[mapped[:,2]==k];overlay=np.zeros(pixels.shape,bool);overlay[points[:,0],points[:,1]]=1
                            ax.contour(overlay.T,levels=[.5],colors=['#ffad32'],linewidths=.8)
                            ax.set_title(f'{c.lesion_key} | plane {k}');ax.set_axis_off()
                        fig.suptitle('Native DICOM grid; supplied mask outline; technical review only',fontsize=10)
                        fig.tight_layout();fig.savefig(output/f'{c.lesion_key}_mask_overlay.png',dpi=150);plt.close(fig)
            mask_records.append(r)
    m=pd.DataFrame(mask_records) if mask_records else pd.DataFrame(columns=['baseline_mask_available','grid_equivalent'])
    file_csv=f.to_csv(index=False).encode()
    (ROOT/f'data/processed/{prefix}_dicom_file_qc.csv').write_bytes(file_csv)
    if prefix!='additional':
        (ROOT/f'data/processed/{prefix}_dicom_file_qc.csv.gz').write_bytes(gzip.compress(file_csv,mtime=0))
    s.to_csv(ROOT/f'data/processed/{prefix}_dicom_series_qc.csv',index=False)
    # Serialize matrices in flat CSV fields; raw numeric matrices stay in JSON.
    flat=m.copy()
    for col in ['mask_to_image_voxel_transform','integer_reindex_transform']:
        if col in flat:flat[col]=flat[col].map(lambda x:json.dumps(x) if isinstance(x,list) else x)
    flat.to_csv(ROOT/f'data/processed/{prefix}_baseline_mask_alignment.csv',index=False)
    summary=dict(scope=scope,studies=len(studies),
        dicom_files=len(f),series_uid_groups=len(s),series_directories=int(f.series_directory.nunique()),
        integrity_verified_files=int((f.sha256_match*f.crc32_match*f.size_match).sum()),
        pixel_decodable_files=int(f.pixel_decodable.sum()),nonfinite_pixel_arrays=int((f.pixel_finite==0).sum()),
        constant_pixel_arrays=int(f.constant_pixel_array.sum()),date_mismatch_files=int((f.study_date_matches_directory==0).sum()),
        duplicate_sop_files=int((f.sop_uid_occurrences>1).sum()),
        regular_geometry_stacks=int(s.geometry_regular.sum()),technical_pass_stacks=int(s.technical_stack_pass.sum()),
        t2_flair_metadata_candidates=int(s.t2_flair_metadata_candidate.sum()),
        t1_flair_names_not_t2_flair=int(s.t1_flair_name.sum()),
        derived_or_projection_groups=int(s.derived_or_projection_hint.sum()),
        spacing_tag_position_mismatch_groups=int(s.spacing_tag_position_mismatch.sum()),
        t2_flair_candidates_with_interslice_gap=int(s.loc[s.t2_flair_metadata_candidate==1,'interslice_gap_present'].sum()),
        contrast_bolus_tag_populated_files=int(f.ContrastBolusAgent.ne('').sum()),
        baseline_lesion_candidates_in_added_studies=len(m),baseline_mask_candidates=int(m.baseline_mask_available.sum()),
        grid_equivalent_masks=int(m.grid_equivalent.sum()),
        engineering_tolerances=dict(direction_or_spacing_abs=1e-4,duplicate_plane_mm=1e-3,
            plane_step_abs_mm=.05,plane_step_relative=.01,affine_residual_mm=.1,grid_corner_voxels=1e-3),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        input_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
            'data/processed/followup_availability_current.csv','data/processed/mask_file_audit.csv',
            'data/raw/openbtai/NIFTIs_Masks.zip']},
        versions={p:importlib.metadata.version(p) for p in ['numpy','pydicom','nibabel']},
        masks=m.where(m.notna(),None).to_dict('records'),
        full_selected_mri_qc_complete=False,clinical_image_review_complete=False,
        contrast_administration_verified=False,registration_performed=False,models_fitted=False,
        next_steps=['Extend all-file QC to previously archived baseline studies',
                    'Verify contrast timing and T2-FLAIR selection before registration',
                    'Resolve lesion-level RN and event-free surveillance evidence before prediction'])
    if mask_candidates_only:
        summary['baseline_lesion_candidates']=summary.pop('baseline_lesion_candidates_in_added_studies')
        summary['next_steps']=['Investigate mask-grid discrepancies without changing source labels',
                              'Restore and audit corresponding FLAIR series before registration',
                              'Resolve lesion-level RN and event-free surveillance evidence before prediction']
    summary['mask_audit_performed']=include_mask_audit
    if not include_mask_audit:
        for key in ['baseline_lesion_candidates_in_added_studies','baseline_mask_candidates','grid_equivalent_masks']:
            summary.pop(key,None)
    # pandas object NaNs in absent columns must be valid JSON nulls.
    def json_safe(v):
        if isinstance(v,dict):return {k:json_safe(x) for k,x in v.items()}
        if isinstance(v,list):return [json_safe(x) for x in v]
        return None if isinstance(v,float) and not np.isfinite(v) else v
    summary=json_safe(summary)
    (ROOT/f'reports/{prefix}_imaging_qc.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False))
    print(json.dumps({k:v for k,v in summary.items() if k!='masks'},indent=2),flush=True)
    return summary


if __name__=='__main__':run()
