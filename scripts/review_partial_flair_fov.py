"""Inspect partial coordinate-FOV cases on native slices; no image resampling."""
from pathlib import Path
import hashlib
import json
import zipfile
import nibabel as nib
import numpy as np
import pandas as pd
import pydicom
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]


def run():
    pairs=pd.read_csv(ROOT/'data/processed/baseline_flair_pairs.csv')
    masks=pd.read_csv(ROOT/'data/processed/cohort_baseline_mask_alignment.csv')
    native=pd.read_csv(ROOT/'data/processed/cohort_dicom_series_qc.csv')
    flair=pd.read_csv(ROOT/'data/processed/flair_dicom_series_qc.csv')
    t1files=pd.read_csv(ROOT/'data/processed/cohort_dicom_file_qc.csv.gz')
    ffiles=pd.read_csv(ROOT/'data/processed/flair_dicom_file_qc.csv.gz')
    out=ROOT/'outputs/flair-grid-qc-20261028';out.mkdir(exist_ok=True,parents=True)
    diagnostics=[]
    def sorted_files(table,uid):
        f=table[table.SeriesInstanceUID==uid].copy()
        o=np.array(json.loads(f.iloc[0].ImageOrientationPatient));normal=np.cross(o[:3],o[3:])
        f['position']=[np.array(json.loads(x))@normal for x in f.ImagePositionPatient]
        return f.sort_values('position').reset_index(drop=True)
    def read_pixels(row):
        p=ROOT/'data/imaging/dicom'/row.member
        if not p.exists():p=ROOT/'data/imaging/current_baseline_addition'/row.member
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row.source_sha256:raise ValueError('Displayed slice SHA mismatch')
        return pydicom.dcmread(p).pixel_array
    with zipfile.ZipFile(ROOT/'data/raw/openbtai/NIFTIs_Masks.zip') as z:
        for r in pairs[pairs.coordinate_fov_fraction.lt(1)].itertuples():
            m=masks[masks.lesion_key==r.lesion_key].iloc[0];f=flair[flair.series_uid==r.flair_series_uid].iloc[0]
            t=native[native.series_uid==m.series_uid].iloc[0]
            name=next(n for n in z.namelist() if Path(n).name==m.mask_file and '__MACOSX' not in n)
            mask=nib.Nifti1Image.from_bytes(z.read(name));arr=np.asanyarray(mask.dataobj)
            coords=np.argwhere((arr//10)==int(r.lesion_key.split('_L')[1]))
            world=(mask.affine[:3,:3]@coords.T).T+mask.affine[:3,3]
            fa=np.array(json.loads(f.affine_ras_json));ta=np.array(json.loads(t.affine_ras_json))
            fv=np.linalg.solve(fa,np.c_[world,np.ones(len(world))].T).T[:,:3]
            tv=np.linalg.solve(ta,np.c_[world,np.ones(len(world))].T).T[:,:3]
            shape=np.array(list(map(int,f.volume_shape_col_row_slice.split('x'))))
            outside=(fv<-.5)|(fv>=shape-.5)
            diagnostics.append(dict(lesion_key=r.lesion_key,target_voxels=len(coords),
                coordinate_inside_voxels=int((~outside.any(1)).sum()),
                outside_columns=int(outside[:,0].sum()),outside_rows=int(outside[:,1].sum()),outside_slices=int(outside[:,2].sum()),
                target_min_flair_voxel_index=fv.min(0).tolist(),target_max_flair_voxel_index=fv.max(0).tolist(),
                flair_shape=shape.tolist(),interpretation='coordinate slice-axis boundary finding; anatomical cause unverified',
                registration_performed=False,image_resampling_performed=False))
            trows=sorted_files(t1files,m.series_uid);frows=sorted_files(ffiles,r.flair_series_uid)
            selections=[('T1 native',trows,int(np.rint(tv[:,2].mean())),tv[:,0:2].mean(0))]
            k0=int(np.clip(np.floor(fv[:,2].mean()),0,len(frows)-2))
            selections.extend((f'FLAIR native plane {k}',frows,k,fv[:,0:2].mean(0)) for k in [k0,k0+1])
            fig,axes=plt.subplots(1,3,figsize=(12,4))
            for ax,(label,rows,k,center) in zip(axes,selections):
                pixels=read_pixels(rows.iloc[k]);lo,hi=np.percentile(pixels,[1,99.5])
                ax.imshow(pixels,cmap='gray',vmin=lo,vmax=hi,origin='lower')
                ax.scatter([center[0]],[center[1]],marker='+',c='#ffb52e',s=75,linewidths=1)
                ax.set_title(label);ax.set_axis_off()
            fig.suptitle(r.lesion_key+' | marker: header-projected target center; no registration',fontsize=10)
            fig.tight_layout();fig.savefig(out/(r.lesion_key+'_native_fov_review.png'),dpi=140);plt.close(fig)
    (ROOT/'reports/partial_flair_fov_review.json').write_text(json.dumps(diagnostics,indent=2,allow_nan=False))
    print(json.dumps(diagnostics,indent=2),flush=True)
    return diagnostics


if __name__=='__main__':run()
