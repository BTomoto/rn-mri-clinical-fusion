from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
specs=[]
for name,file in [('OutcomeAudit','outcome_timing_audit'),('BaselineFeatures','baseline_existing_features'),('MaskFiles','mask_file_audit'),
                  ('MaskLesions','mask_lesion_audit'),('DICOMSamples','dicom_sample_audit')]:
    df=pd.read_csv(ROOT/f'data/processed/{file}.csv',dtype={'patient_id':str,'Patient':str,'Timepoint':str,'study_date_code':str,'baseline_mask_date_code':str,'baseline_actual_mask_date_code':str})
    # Keep identifiers as text; all measurements remain numeric.
    for col in ['baseline_date_code']:
        if col in df:df[col]=df[col].map(lambda x: str(int(x)) if pd.notna(x) else None)
    specs.append(dict(name=name,headers=df.columns.tolist(),rows=json.loads(df.to_json(orient='values'))))
ev=json.loads((ROOT/'data/metadata/endpoint_evidence/reviewed_sources.json').read_text())
df=pd.DataFrame(ev).fillna('')
specs.append(dict(name='Evidence',headers=df.columns.tolist(),rows=df.values.tolist()))
data=dict(sheets=specs,summary=json.loads((ROOT/'reports/readiness_audit.json').read_text()))
(ROOT/'reports/readiness_workbook_input.json').write_text(json.dumps(data,ensure_ascii=False))
print('Prepared',[(s['name'],len(s['rows'])) for s in specs])
