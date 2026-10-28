"""Prepare typed QC data for the artifact-tool Excel builder."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
specs=[
 ('Series','additional_dicom_series_qc.csv',['patient_id','study_date_code','series_name','files','technical_stack_pass','slice_step_mm','SpacingBetweenSlices','spacing_tag_position_mismatch','SliceThickness','interslice_gap_present','t2_flair_metadata_candidate','t1_flair_name','derived_or_projection_hint','contrast_administration_verified','SeriesDescription','geometry_reason','affine_position_residual_mm']),
 ('Lesions','additional_baseline_mask_alignment.csv',['lesion_key','patient_id','study_date_code','baseline_mask_available','grid_equivalent','alignment_status','max_corner_error_voxels','target_voxels','target_voxels_inside_image','anatomical_review_complete','use_for_model']),
 ('Files','additional_dicom_file_qc.csv',['patient_id','study_date_code','member','sha256_match','size_match','crc32_match','pixel_decodable','pixel_finite','pixel_shape','pixel_shape_matches_header','constant_pixel_array','pixel_min','pixel_max','study_date_matches_directory','sop_uid_occurrences','source_sha256'])]
sheets=[]
for name,file,cols in specs:
    df=pd.read_csv(ROOT/'data/processed'/file,dtype={'patient_id':str,'study_date_code':str}).reindex(columns=cols)
    sheets.append(dict(name=name,headers=cols,rows=df.astype(object).where(df.notna(),None).values.tolist()))
(ROOT/'reports/imaging_qc_workbook_input.json').write_text(json.dumps(dict(sheets=sheets),ensure_ascii=False,allow_nan=False))
print('Prepared 3 QC tables')
