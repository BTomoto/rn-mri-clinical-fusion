from pathlib import Path
import json
import pandas as pd

root=Path(__file__).resolve().parents[1]
specs=[]
for name,file in [('ClinicalCurrent','clinical_current'),('EndpointChanges','clinical_version_changes'),
                  ('Followup','followup_availability_current'),('Horizon','horizon_availability_current'),
                  ('BaselineFeatures','baseline_features_current')]:
    d=pd.read_csv(root/f'data/processed/{file}.csv',keep_default_na=False,na_values=[''],dtype={'patient_id':str,'patient_id_source':str,'baseline_mask_date_code':str,'Timepoint':str,'Patient':str})
    if name=='EndpointChanges':
        d=d[d.field.isin(['rn_time_day','first_srs_start_day'])].copy()
        d['figshare_value']=pd.to_numeric(d.figshare_value,errors='coerce')
        d['molab_current_value']=pd.to_numeric(d.molab_current_value,errors='coerce')
    specs.append(dict(name=name,headers=d.columns.tolist(),rows=json.loads(d.to_json(orient='values'))))
d=pd.read_csv(root/'data/metadata/endpoint_followup/source_checks.csv')
specs.append(dict(name='Sources',headers=d.columns.tolist(),rows=json.loads(d.to_json(orient='values'))))
summary=json.loads((root/'reports/endpoint_followup_summary.json').read_text())
(root/'reports/endpoint_workbook_input.json').write_text(json.dumps(dict(sheets=specs,summary=summary),ensure_ascii=False))
print('Prepared',[(s['name'],len(s['rows'])) for s in specs])
