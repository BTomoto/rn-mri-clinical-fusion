"""Fixed eight-feature extraction on the available mirror cohort; no model fitting."""
from pathlib import Path
import concurrent.futures as cf
import datetime as dt
import gzip,hashlib,itertools,json
import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage

from .ucsd_mri_mirror import download_asset
from .ucsd_mri_intake import sha256,valid_affine,corner_delta
from .ucsd_roi_pilot import region_union,percentile_parameters,fixed_bins
from .ucsd_intensity_followup import affine_values

SEQUENCES=('FLAIR','T1post','BraTS_tumor_seg')
SUFFIXES=('mean','std','entropy','glcm_contrast')
FEATURES=tuple(f'{s}_{f}' for s in SEQUENCES[:2] for f in SUFFIXES)
OFFSETS=tuple(t for t in itertools.product((-1,0,1),repeat=3) if t!=(0,0,0) and next(x for x in t if x)!=-1)


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    part=path.with_name(path.name+'.partial');part.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');part.replace(path)


def prepare(root):
    root=Path(root);cohort=pd.read_csv(root/'data/processed/ucsd_clinical_revalidated_cohort.csv')
    inv=pd.read_csv(root/'data/metadata/ucsd_mirror_asset_inventory.csv')
    meta=pd.read_csv(root/'data/raw/reference/ucsd_mirror_participants.tsv',sep='\t',encoding='cp1252')
    meta['clinical_ID']=meta.ID.str.replace('sub-','UCSD-PTGBM-',regex=False)
    if meta.clinical_ID.duplicated().any() or inv.duplicated(['ID','sequence']).any():raise ValueError('ambiguous_source_ID')
    selected=inv[inv.ID.isin(cohort.ID)&inv.sequence.isin(SEQUENCES)].sort_values(['ID','sequence']).reset_index(drop=True)
    ids=selected.groupby('ID').sequence.nunique();ids=set(ids[ids.eq(3)].index)
    selected=selected[selected.ID.isin(ids)].copy()
    target=cohort[cohort.ID.isin(ids)].copy().sort_values('ID')
    if len(target)!=182 or len(selected)!=546 or int(selected.bytes.sum())>650*1024**2:raise ValueError('pinned_target_manifest_changed')
    binding=target[['ID','BraTS ID']].merge(meta[['clinical_ID','BraTS ID']],left_on='ID',right_on='clinical_ID',suffixes=('_clinical','_mirror'),validate='one_to_one')
    if not binding['BraTS ID_clinical'].eq(binding['BraTS ID_mirror']).all():raise ValueError('BraTS_ID_mismatch')
    selected['storage']=selected.mirror_filename.map(lambda n:'existing_git_sample' if (root/'data/samples/ucsd_mirror'/n).exists() else 'batch_package')
    out=root/'reports/ucsd_batch_features';out.mkdir(parents=True,exist_ok=True)
    selected.to_csv(out/'source_manifest.csv',index=False)
    target[['ID','patient_id','BraTS ID','brats_patient_id','validation_group','tumor_label','label_source']].to_csv(out/'target_cases.csv',index=False)
    return cohort,target,selected


def local_path(root,batch_root,record):
    return (Path(root)/'data/samples/ucsd_mirror'/record['mirror_filename'] if record['storage']=='existing_git_sample'
            else Path(batch_root)/record['mirror_filename'])


def download_all(root,batch_root,manifest,workers=6):
    out=Path(root)/'reports/ucsd_batch_features';rows=[]
    def one(rec):
        r={k:rec[k] for k in ['ID','sequence','mirror_filename','storage','url']};r['success']=False
        try:
            d=download_asset(rec,local_path(root,batch_root,rec));d.pop('path',None);r.update(d,success=True)
        except Exception as exc:r['error']=type(exc).__name__+': '+str(exc)
        return r
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        tasks=[pool.submit(one,r) for r in manifest.to_dict('records')]
        for future in cf.as_completed(tasks):
            rows.append(future.result())
            if len(rows)%30==0 or len(rows)==len(tasks):
                write_json(out/'download_progress.json',dict(completed=len(rows),requested=len(tasks),successful=sum(x['success'] for x in rows),checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat()))
                print(f"Transfers checked {len(rows)}/{len(tasks)}; available {sum(x['success'] for x in rows)}",flush=True)
    rows.sort(key=lambda x:(x['ID'],x['sequence']));write_json(out/'download_receipt.json',dict(files=rows))
    return rows


def read_actual(path,record):
    """Complete gzip + native array read without an unnecessary float64 image copy."""
    path=Path(path)
    if not path.is_file() or path.is_symlink():raise ValueError('missing_or_nonregular_source_file')
    if path.stat().st_size!=int(record['bytes']) or sha256(path)!=record['sha256']:raise ValueError('source_size_or_digest_mismatch')
    total=0
    with gzip.open(path,'rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):
            total+=len(block)
            if total>512*1024**2:raise ValueError('decompressed_size_limit')
    img=nib.load(path,mmap=False);shape=tuple(img.shape)
    if len(shape)!=3 or min(shape)<2 or np.prod(shape,dtype=object)>40_000_000:raise ValueError('unsupported_image_shape')
    if not valid_affine(img.affine):raise ValueError('invalid_native_affine')
    q,qc=img.get_qform(coded=True);s,sc=img.get_sform(coded=True)
    if not qc and not sc:raise ValueError('fallback_coordinates_only')
    if qc and sc and (qc!=sc or not valid_affine(q) or not valid_affine(s) or corner_delta(shape,q,s)>1e-6):raise ValueError('coded_forms_disagree')
    a=np.asarray(img.dataobj)
    if a.dtype.kind not in 'iuf' or not np.isfinite(a).all():raise ValueError('nonfinite_or_nonreal_voxels')
    r=dict(ID=record['ID'],sequence=record['sequence'],mirror_filename=record['mirror_filename'],storage=record['storage'],
           bytes=int(record['bytes']),sha256=record['sha256'],decoded=True,gzip_crc_verified=True,digest_matches=True,
           shape=list(shape),dtype=str(img.get_data_dtype()),spatial_units=img.header.get_xyzt_units()[0],
           native_affine=img.affine.tolist(),form_code=int(sc or qc),minimum=float(a.min()),maximum=float(a.max()),
           slope=float(img.dataobj.slope),intercept=float(img.dataobj.inter),physical_scale_confirmed=False)
    return img,a,r


def symmetric_merged_glcm(bins,roi,n_bins=32):
    b=np.asarray(bins);mask=np.asarray(roi,dtype=bool)
    if b.shape!=mask.shape or b.ndim!=3 or not mask.any():raise ValueError('invalid_GLCM_input')
    if (b[mask]<1).any() or (b[mask]>n_bins).any():raise ValueError('GLCM_bin_out_of_range')
    loc=np.where(mask);bbox=tuple(slice(int(x.min()),int(x.max())+1) for x in loc)
    b=b[bbox];mask=mask[bbox];matrix=np.zeros((n_bins,n_bins),dtype=np.int64);used=0
    for offset in OFFSETS:
        left=tuple(slice(max(0,-d),b.shape[k]-max(0,d)) for k,d in enumerate(offset))
        right=tuple(slice(max(0,d),b.shape[k]-max(0,-d)) for k,d in enumerate(offset))
        pair=mask[left]&mask[right]
        if not pair.any():continue
        used+=1;x=b[left][pair].astype(np.int64)-1;y=b[right][pair].astype(np.int64)-1
        counts=np.bincount(x*n_bins+y,minlength=n_bins*n_bins).reshape(n_bins,n_bins)
        matrix+=counts+counts.T
    total=int(matrix.sum())
    if not total:raise ValueError('no_valid_ROI_neighbour_pairs')
    return matrix/total,total,used


def sequence_features(image,roi,eroded):
    params=percentile_parameters(image);v=affine_values(np.asarray(image)[roi],params)
    quantized,lo,hi=fixed_bins(v)
    bins=np.zeros(roi.shape,dtype=np.uint8);bins[roi]=quantized
    def calculate(mask,values):
        counts=np.bincount(bins[mask],minlength=33)[1:];p=counts/counts.sum();p=p[p>0]
        glcm,n_pairs,n_dirs=symmetric_merged_glcm(bins,mask)
        difference=np.arange(32)[:,None]-np.arange(32)[None,:]
        values=dict(mean=float(values.mean()),std=float(values.std(ddof=0)),
                    entropy=float(-np.sum(p*np.log2(p))),glcm_contrast=float(np.sum(glcm*difference**2)))
        return values,n_pairs,n_dirs
    primary,n_pairs,n_dirs=calculate(roi,v)
    eroded_values=None;error=None;eroded_pairs=None
    if eroded.any():
        try:eroded_values,eroded_pairs,_=calculate(eroded,affine_values(np.asarray(image)[eroded],params))
        except ValueError as exc:error=str(exc)
    else:error='empty_eroded_ROI'
    diag=dict(**params,bin_minimum=lo,bin_maximum=hi,occupied_bins=int(np.unique(quantized).size),
              neighbour_pairs_symmetric=n_pairs,directions_with_pairs=n_dirs,
              eroded_pairs_symmetric=eroded_pairs,erosion_error=error,
              normalized_minimum=float(v.min()),normalized_maximum=float(v.max()))
    return primary,eroded_values,diag


def process_case(root,batch_root,case,records,fingerprint):
    cache=Path(batch_root).parent/'ucsd_batch_feature_checkpoints'/f'{case}.json'
    signature=dict(fingerprint=fingerprint,inputs={r['sequence']:r['sha256'] for r in records})
    if cache.exists():
        saved=json.loads(cache.read_text())
        valid_inputs=all(local_path(root,batch_root,r).is_file() and
                         not local_path(root,batch_root,r).is_symlink() and
                         local_path(root,batch_root,r).stat().st_size==int(r['bytes']) and
                         sha256(local_path(root,batch_root,r))==r['sha256'] for r in records)
        if saved.get('signature')==signature and saved.get('result',{}).get('status')=='complete' and valid_inputs:
            return saved['result']
    result=dict(ID=case,status='processing_failed',primary=None,eroded=None,diagnostics=[],file_QC=[],error=None)
    try:
        loaded={}
        for r in records:
            try:
                img,a,q=read_actual(local_path(root,batch_root,r),r);loaded[r['sequence']]=(img,a,q);result['file_QC'].append(q)
            except Exception as exc:
                result['file_QC'].append(dict(ID=r['ID'],sequence=r['sequence'],mirror_filename=r['mirror_filename'],
                    storage=r['storage'],decoded=False,digest_matches=False,gzip_crc_verified=False,
                    error=type(exc).__name__+': '+str(exc)))
        if len(loaded)!=3:raise ValueError('source_file_QC_failed')
        ref=loaded['FLAIR'][2]
        for seq,(_,a,q) in loaded.items():
            if q['shape']!=ref['shape'] or q['spatial_units']!=ref['spatial_units'] or q['form_code']!=ref['form_code'] or corner_delta(q['shape'],q['native_affine'],ref['native_affine'])>1e-6:raise ValueError('relative_grid_mismatch: '+seq)
            q['relative_grid_match']=True
        roi=region_union(loaded['BraTS_tumor_seg'][1])
        if roi.all():raise ValueError('full_array_annotation_mask')
        eroded=ndimage.binary_erosion(roi,structure=ndimage.generate_binary_structure(3,1),iterations=1)
        result.update(roi_voxels=int(roi.sum()),eroded_voxels=int(eroded.sum()),erosion_retention=float(eroded.sum()/roi.sum()))
        primary={};sensitivity={}
        for seq in SEQUENCES[:2]:
            p,e,diag=sequence_features(loaded[seq][1],roi,eroded)
            primary.update({f'{seq}_{k}':v for k,v in p.items()})
            sensitivity.update({f'{seq}_{k}':None if e is None else e[k] for k in SUFFIXES})
            result['diagnostics'].append(dict(ID=case,sequence=seq,**diag))
        if not all(np.isfinite(primary[k]) for k in FEATURES):raise ValueError('incomplete_or_nonfinite_primary_features')
        result.update(status='complete',primary=primary,eroded=sensitivity)
    except Exception as exc:result['error']=type(exc).__name__+': '+str(exc)
    write_json(cache,dict(signature=signature,result=result))
    return result


def fingerprint(root):
    root=Path(root);parts={p:sha256(root/p) for p in ['reports/ucsd_batch_features_protocol.md',
        'src/rn_public/ucsd_batch_features.py','src/rn_public/ucsd_roi_pilot.py','src/rn_public/ucsd_intensity_followup.py']}
    return hashlib.sha256(json.dumps(parts,sort_keys=True).encode()).hexdigest(),parts


def run(root,batch_root=None,download=True,workers=4):
    root=Path(root);batch_root=Path(batch_root) if batch_root else root.parent/'ucsd_batch_sources'
    cohort,target,manifest=prepare(root);out=root/'reports/ucsd_batch_features'
    if download:transfers=download_all(root,batch_root,manifest)
    else:transfers=json.loads((out/'download_receipt.json').read_text())['files']
    fp,parts=fingerprint(root);results=[]
    def one(case):return process_case(root,batch_root,case,manifest[manifest.ID.eq(case)].to_dict('records'),fp)
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        tasks=[pool.submit(one,c) for c in target.ID]
        for f in cf.as_completed(tasks):
            results.append(f.result())
            if len(results)%15==0 or len(results)==len(tasks):
                write_json(out/'processing_progress.json',dict(completed=len(results),requested=len(tasks),complete_features=sum(r['status']=='complete' for r in results)))
                print(f"Cases processed {len(results)}/{len(tasks)}; complete {sum(r['status']=='complete' for r in results)}",flush=True)
    results.sort(key=lambda r:r['ID'])
    ok=[r for r in results if r['status']=='complete']
    primary=pd.DataFrame([dict(ID=r['ID'],**r['primary']) for r in ok],columns=['ID',*FEATURES])
    eroded=pd.DataFrame([dict(ID=r['ID'],**r['eroded']) for r in ok],columns=['ID',*FEATURES])
    primary.to_csv(root/'data/processed/ucsd_image_features.csv',index=False)
    eroded.to_csv(root/'data/processed/ucsd_image_features_eroded.csv',index=False)
    joined=cohort.merge(primary,on='ID',how='inner',validate='one_to_one');joined.to_csv(root/'data/processed/ucsd_clinical_image_features.csv',index=False)
    target_status=pd.DataFrame([dict(ID=r['ID'],status=r['status'],error=r['error'],roi_voxels=r.get('roi_voxels'),eroded_voxels=r.get('eroded_voxels'),erosion_retention=r.get('erosion_retention'),eroded_complete=r.get('eroded') is not None and all(v is not None for v in r['eroded'].values())) for r in results])
    all_status=cohort.merge(target_status,on='ID',how='left',validate='one_to_one');all_status['status']=all_status.status.fillna('not_listed_in_current_mirror')
    all_status.to_csv(out/'all_clinical_case_status.csv',index=False)
    pd.DataFrame([d for r in results for d in r['diagnostics']]).to_csv(out/'normalization_and_texture_diagnostics.csv',index=False)
    qc=[q for r in results for q in r['file_QC']]
    flat=[{k:(json.dumps(v) if isinstance(v,list) else v) for k,v in q.items()} for q in qc]
    pd.DataFrame(flat).to_csv(out/'actual_file_QC.csv',index=False)
    differences=eroded.set_index('ID')[list(FEATURES)]-primary.set_index('ID')[list(FEATURES)]
    differences.to_csv(out/'eroded_minus_primary_features.csv')
    summary=dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),clinical_timepoints=len(cohort),clinical_source_patients=int(cohort.patient_id.nunique()),
        target_timepoints=len(target),target_source_patients=int(target.patient_id.nunique()),target_files=len(manifest),
        declared_target_bytes=int(manifest.bytes.sum()),available_source_files=sum(r['success'] for r in transfers),
        available_source_bytes=sum(r.get('bytes',0) for r in transfers if r['success']),
        primary_complete_timepoints=len(primary),primary_source_patients=int(joined.patient_id.nunique()),
        primary_tumor_timepoints=int(joined.tumor_label.sum()),primary_treatment_change_timepoints=int(joined.tumor_label.eq(0).sum()),
        target_failed_timepoints=len(target)-len(primary),not_listed_timepoints=int(all_status.status.eq('not_listed_in_current_mirror').sum()),
        eroded_complete_timepoints=int(target_status.eroded_complete.sum()),feature_count=len(FEATURES),feature_names=list(FEATURES),
        files_decoded=sum(q['decoded'] for q in qc),unknown_spatial_unit_files=sum(q.get('spatial_units')=='unknown' for q in qc),
        MRI_model_fitted=False,clinical_model_refitted=False,classification_metrics_computed=False,
        feature_selection_by_outcome=False,physical_volume_features=False,quantitative_ADC_features=False,
        protocol_and_code_sha256=parts,checkpoint_fingerprint=fp,next_step_requires_user_approval=True)
    write_json(out/'batch_receipt.json',dict(summary=summary,cases=results))
    return summary
