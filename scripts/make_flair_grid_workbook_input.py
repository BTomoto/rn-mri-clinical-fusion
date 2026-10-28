"""Prepare typed grid-review and FLAIR pairing records for Excel."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
specs=[
 ('Pairs','baseline_flair_pairs.csv',['lesion_key','patient_id','study_date_code','flair_candidate_found','flair_series_name','coordinate_fov_fraction','coordinate_fov_inside_voxels','target_voxels','flair_interslice_gap_present','FrameOfReferenceUID_comparison','t1_mask_grid_equivalent','pair_status','registration_performed','use_for_model']),
 ('GridReview','grid_precision_review.csv',['lesion_key','qform_sform_corner_difference_mm','sform_dicom_corner_difference_mm','qform_dicom_corner_difference_mm','qform_grid_equivalent','closer_anchor','nifti_slice_step_mm','dicom_endpoint_slice_step_mm','nearest_end_pair_step_difference_mm','review_resolved','source_header_changed']),
 ('FLAIRSeries','flair_dicom_series_qc.csv',['patient_id','study_date_code','series_name','files','technical_stack_pass','slice_step_mm','SliceThickness','interslice_gap_present','EchoTime','InversionTime','derived_or_projection_hint','anatomical_review_complete']),
 ('Files','flair_dicom_file_qc.csv.gz',['patient_id','study_date_code','member','sha256_match','crc32_match','pixel_decodable','constant_pixel_array','pixel_min','pixel_max','source_sha256'])]
sheets=[]
for name,file,cols in specs:
    df=pd.read_csv(ROOT/'data/processed'/file,dtype={'patient_id':str,'study_date_code':str}).reindex(columns=cols)
    sheets.append(dict(name=name,headers=cols,rows=df.astype(object).where(df.notna(),None).values.tolist()))
(ROOT/'reports/flair_grid_workbook_input.json').write_text(json.dumps(dict(sheets=sheets),ensure_ascii=False,allow_nan=False))
print('Prepared FLAIR and grid-review tables')
