"""Read-only checks of saved OOF workbooks, executed notebook and locked analysis code."""
from pathlib import Path
import base64,hashlib,json,sys
import nbformat
import numpy as np
import pandas as pd
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_clinical_baseline import sha256
s=json.loads((ROOT/'reports/ucsd_clinical_revalidation/metrics.json').read_text())
file=ROOT/'outputs/ucsd-clinical-revalidation-20261029/UCSD_Clinical_Revalidation.xlsx'
w=load_workbook(file,read_only=True,data_only=True)
assert w.sheetnames==['Summary','OOF','Folds','Sensitivity','Scope']
def compare(sheet,csv,start=1):
    d=pd.read_csv(ROOT/csv)
    rows=list(w[sheet].iter_rows(min_row=start,max_row=start+len(d),max_col=len(d.columns),values_only=True))
    x=pd.DataFrame(rows[1:],columns=rows[0]);assert x.columns.tolist()==d.columns.tolist()
    for key in d:
        if pd.api.types.is_numeric_dtype(d[key]):np.testing.assert_allclose(pd.to_numeric(x[key]),d[key],rtol=1e-9,atol=1e-9,equal_nan=True)
        else:assert x[key].fillna('').tolist()==d[key].fillna('').tolist(),(sheet,key)
    return d
d=compare('OOF','data/processed/ucsd_clinical_revalidated_oof.csv')
compare('Folds','reports/ucsd_clinical_revalidation/fold_metrics.csv')
secondary=compare('Sensitivity','reports/ucsd_clinical_revalidation/complete_interval_sensitivity_oof.csv',start=11)
compare('Scope','reports/ucsd_clinical_revalidation/excluded_identity_conflicts.csv',start=13)
assert [w['Summary'][k].value for k in ['C5','C6','C8','C9']]==[238,176,5,46]
for row,model in [(13,'M0'),(14,'M1'),(15,'prior')]:
    assert np.isclose(w['Summary'][f'C{row}'].value,s['metrics'][model]['roc_auc'])
    assert np.isclose(w['Summary'][f'F{row}'].value,s['metrics'][model]['brier'])
assert [w['Summary'][k].value for k in ['C25','D25','E25','F25']]==[5,46,4,183]
assert w['Summary']['F19'].value==w['Summary']['F20'].value=='区间跨0'
errors={'#REF!','#DIV/0!','#VALUE!','#NAME?','#NUM!','#NULL!','#SPILL!','#CALC!'}
for name,cols,rows in [('Summary',10,30),('OOF',25,239),('Folds',19,33),('Sensitivity',22,203),('Scope',6,34)]:
    assert not any(isinstance(v,str) and v in errors for row in w[name].iter_rows(max_col=cols,max_row=rows,values_only=True) for v in row)
w.close()
w=load_workbook(file,read_only=True,data_only=False)
assert w['Summary']['F14'].value.startswith('=AVERAGE(')
head=[c.value for c in next(w['OOF'].iter_rows(max_row=1))]
assert any(w['OOF'].cell(2,j+1).value.startswith('=IF(') for j,key in enumerate(head) if key=='M1_prediction_0_5')
w.close()
nb=nbformat.read(ROOT/'notebooks/13_ucsd_clinical_revalidation.ipynb',as_version=4)
cells=[c for c in nb.cells if c.cell_type=='code'];receipt=json.loads((ROOT/'reports/kernel_execution_13.json').read_text())
assert receipt['success'] and receipt['notebooks'][0]['errors']==0 and len(cells)==5
assert all(c.execution_count is not None for c in cells)
assert receipt['notebooks'][0]['code_sha256']==hashlib.sha256('\n'.join(c.source for c in cells).encode()).hexdigest()
figure=ROOT/'outputs/ucsd-clinical-revalidation-20261029/clinical_revalidation_comparison.png'
attachments=[c.attachments['clinical.png']['image/png'] for c in nb.cells if c.cell_type=='markdown' and c.metadata.get('plot_attachment')]
assert len(attachments)==1 and base64.b64decode(attachments[0])==figure.read_bytes()
assert s['analysis_code_sha256']==sha256(ROOT/'src/rn_public/ucsd_clinical_revalidation.py')
assert s['protocol_sha256']==sha256(ROOT/'reports/ucsd_clinical_revalidation_protocol.md')
report=dict(success=True,main_OOF_records_verified=len(d),secondary_OOF_records_verified=len(secondary),identity_exclusions_verified=5,
            excel_formula_errors=0,formula_input_change_check=True,notebook_code_cells=5,notebook_errors=0,
            figure_attachment_verified=True,workbook_sha256=sha256(file),protocol_sha256=s['protocol_sha256'],
            analysis_code_sha256=s['analysis_code_sha256'],note='Formulas recalculated by artifact-tool, not native Excel; no MRI pixel QC claimed')
(ROOT/'reports/ucsd_clinical_revalidation/artifact_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
