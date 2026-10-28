"""Prepare current-cohort QC tables for the Excel builder."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
specs=[
 ('Lesions','cohort_baseline_mask_alignment.csv',['lesion_key','patient_id','study_date_code','grid_equivalent','max_corner_error_voxels','max_corner_error_mm','target_voxels','target_voxels_inside_image_fov','target_voxels_on_constant_slices','target_max_reindex_error_mm','alignment_status','name_match_rule','mask_series_name','dicom_series_name','anatomical_review_complete','use_for_model']),
 ('Series','cohort_dicom_series_qc.csv',['patient_id','study_date_code','series_name','files','technical_stack_pass','constant_slices','slice_step_mm','SpacingBetweenSlices','spacing_tag_position_mismatch','derived_or_projection_hint','affine_position_residual_mm','affine_step_estimator']),
 ('Files','cohort_dicom_file_qc.csv.gz',['patient_id','study_date_code','member','sha256_match','crc32_match','pixel_decodable','constant_pixel_array','pixel_min','pixel_max','source_sha256'])]
sheets=[]
for name,filename,cols in specs:
    df=pd.read_csv(ROOT/'data/processed'/filename,dtype={'patient_id':str,'study_date_code':str}).reindex(columns=cols)
    sheets.append(dict(name=name,headers=cols,rows=df.astype(object).where(df.notna(),None).values.tolist()))
summary=json.loads((ROOT/'reports/cohort_imaging_qc.json').read_text())
(ROOT/'reports/baseline_qc_workbook_input.json').write_text(json.dumps(dict(sheets=sheets,summary=summary),ensure_ascii=False,allow_nan=False))
print('Prepared baseline QC workbook data')
