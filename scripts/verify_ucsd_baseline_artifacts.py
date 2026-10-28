"""Read-only checks of saved Excel, CSV, notebook execution and source fingerprints."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
import nbformat
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_clinical_baseline import make_cohort, sha256
s=json.loads((ROOT/'reports/ucsd_clinical_baseline/metrics.json').read_text())
cohort=make_cohort(ROOT)
d=pd.read_csv(ROOT/'data/processed/ucsd_clinical_oof_predictions.csv')
path=ROOT/'outputs/ucsd-clinical-baseline-20261029/UCSD_Clinical_Baseline.xlsx'
w=load_workbook(path,read_only=True,data_only=True)
assert w.sheetnames==['Summary','Timepoints','Folds']
rows=list(w['Timepoints'].iter_rows(min_row=1,max_row=244,min_col=1,max_col=21,values_only=True))
x=pd.DataFrame(rows[1:],columns=rows[0])
assert x.ID.tolist()==cohort.ID.tolist()==d.ID.tolist()
for key in d.columns:
    if pd.api.types.is_numeric_dtype(d[key]):
        np.testing.assert_allclose(pd.to_numeric(x[key]),d[key],rtol=1e-10,atol=1e-10,equal_nan=True)
    else:
        assert x[key].fillna('').tolist()==d[key].fillna('').tolist(), key
np.testing.assert_allclose(x.logistic_squared_error,(d.tumor_label-d.oof_tumor_probability)**2,atol=1e-12)
summary=w['Summary']
assert [summary[k].value for k in ['C5','C6','C7','C8']]==[243,178,192,51]
assert [summary[k].value for k in ['C21','D21','E21','F21']]==[0,51,3,189]
for cell,key in [('C13','roc_auc'),('C16','brier'),('C23','sensitivity_tumor'),('E23','specificity_treatment_change'),('C24','balanced_accuracy')]:
    assert np.isclose(summary[cell].value,s['logistic_oof'][key])
errors={'#REF!','#DIV/0!','#VALUE!','#NAME?','#NUM!','#NULL!','#SPILL!','#CALC!'}
for name,cols,last in [('Summary',8,24),('Timepoints',25,244),('Folds',13,13)]:
    assert not any(isinstance(v,str) and v in errors for row in w[name].iter_rows(max_row=last,max_col=cols,values_only=True) for v in row)
w.close()
w=load_workbook(path,read_only=True,data_only=False)
assert w['Summary']['C16'].value.startswith('=AVERAGE(')
assert w['Timepoints']['T244'].value=='=(C244-Q244)^2'
w.close()
receipt=json.loads((ROOT/'reports/kernel_execution_11.json').read_text())
nb=nbformat.read(ROOT/'notebooks/11_ucsd_clinical_baseline.ipynb',as_version=4)
codes=[c for c in nb.cells if c.cell_type=='code']
assert receipt['success'] and receipt['notebooks'][0]['errors']==0
assert receipt['notebooks'][0]['code_sha256']==hashlib.sha256('\n'.join(c.source for c in codes).encode()).hexdigest()
assert len(codes)==5 and all(c.execution_count is not None for c in codes)
assert s['analysis_code_sha256']==sha256(ROOT/'src/rn_public/ucsd_clinical_baseline.py')
assert s['protocol_sha256']==sha256(ROOT/'reports/ucsd_clinical_baseline_protocol.md')
report=dict(success=True,excel_timepoints_verified=243,excel_formula_errors=0,excel_formula_input_change_check=True,
            rendered_views_reviewed=['Summary','Timepoints','Sources','Definitions','Folds','Parameters'],
            notebook_code_cells=5,notebook_errors=0,source_fingerprints_verified=True,
            workbook_sha256=sha256(path),OOF_csv_sha256=sha256(ROOT/'data/processed/ucsd_clinical_oof_predictions.csv'),
            note='Read-only saved-file checks; Excel formulas recalculated by artifact-tool, not native Excel')
(ROOT/'reports/ucsd_clinical_baseline/artifact_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
