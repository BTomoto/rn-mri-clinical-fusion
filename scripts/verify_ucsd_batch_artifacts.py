"""Read-only reconciliation of Stage17 data, executed Notebook and Excel."""
from pathlib import Path
import base64,hashlib,json,math,subprocess,sys
import nbformat,numpy as np,pandas as pd
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_batch_features import FEATURES,local_path


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
 out=ROOT/'reports/ucsd_batch_features';r=json.loads((out/'batch_receipt.json').read_text());s=r['summary']
 m=pd.read_csv(out/'source_manifest.csv');q=pd.read_csv(out/'actual_file_QC.csv')
 a=pd.read_csv(ROOT/'data/processed/ucsd_image_features.csv');b=pd.read_csv(ROOT/'data/processed/ucsd_image_features_eroded.csv')
 j=pd.read_csv(ROOT/'data/processed/ucsd_clinical_image_features.csv');c=pd.read_csv(out/'all_clinical_case_status.csv')
 assert len(m)==len(q)==546 and len(a)==len(j)==182 and len(c)==238
 assert m[['ID','sequence']].equals(q[['ID','sequence']])
 for row in m.to_dict('records'):
  p=local_path(ROOT,ROOT.parent/'ucsd_batch_sources',row)
  assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
 assert q[['decoded','digest_matches','gzip_crc_verified','relative_grid_match']].all().all()
 assert q.spatial_units.eq('unknown').all() and q.dtype.eq('uint8').all()
 assert list(a)==['ID',*FEATURES] and list(b)==['ID',*FEATURES]
 assert a.ID.is_unique and set(a.ID)==set(j.ID)==set(c.loc[c.status.eq('complete'),'ID'])
 assert j.patient_id.nunique()==j.validation_group.nunique()==135
 assert np.isfinite(a[list(FEATURES)]).all().all() and np.isfinite(b[list(FEATURES)]).all().all()
 clinical=pd.read_csv(ROOT/'data/processed/ucsd_clinical_revalidated_cohort.csv')
 pd.testing.assert_frame_equal(j[clinical.columns],clinical[clinical.ID.isin(a.ID)].reset_index(drop=True))
 differences=pd.read_csv(out/'eroded_minus_primary_features.csv').set_index('ID')
 np.testing.assert_allclose(differences[list(FEATURES)],b.set_index('ID')[list(FEATURES)]-a.set_index('ID')[list(FEATURES)],atol=1e-12)
 for p,h in s['protocol_and_code_sha256'].items():assert digest(ROOT/p)==h
 assert not s['MRI_model_fitted'] and not s['classification_metrics_computed']
 # Preserve every previously tracked artifact except the three status/document files.
 changed=subprocess.check_output(['git','diff','247986eb96c845ad5cd6534a2f7949f194a8575b','--name-only'],cwd=ROOT,text=True).splitlines()
 prior_changed=[]
 for p in changed:
  existed=subprocess.run(['git','cat-file','-e','247986eb96c845ad5cd6534a2f7949f194a8575b:'+p],cwd=ROOT,capture_output=True).returncode==0
  if existed and p not in ['README.md','.gitignore','reports/project_status.json']:prior_changed.append(p)
 assert not prior_changed,prior_changed
 nb=nbformat.read(ROOT/'notebooks/17_ucsd_batch_image_features.ipynb',as_version=4)
 kr=json.loads((ROOT/'reports/kernel_execution_17.json').read_text());assert kr['success']
 source='\n'.join(cell.source for cell in nb.cells if cell.cell_type=='code')
 assert hashlib.sha256(source.encode()).hexdigest()==kr['notebooks'][0]['code_sha256']
 code=[cell for cell in nb.cells if cell.cell_type=='code'];assert len(code)==5
 assert [cell.execution_count for cell in code]==[1,2,3,4,5]
 assert not [o for cell in code for o in cell.outputs if o.output_type=='error']
 images=[base64.b64decode(o.data['image/png']) for cell in code for o in cell.outputs if o.output_type in ['display_data','execute_result'] and 'image/png' in o.data]
 assert len(images)==2
 for data,name in zip(images,['coverage.png','boundary_deltas.png']):assert data==(ROOT/'figures/ucsd_batch_features'/name).read_bytes()
 payload=json.loads((ROOT/'reports/ucsd_batch_workbook_input.json').read_text())
 xlsx=ROOT/'outputs/ucsd-batch-features-20261029/UCSD_Clinical_Image_Features.xlsx'
 wb=load_workbook(xlsx,read_only=True,data_only=True)
 count=0
 for name in ['Features','Sensitivity','Cases','Files','Definitions','Diagnostics']:
  expected=payload['datasets'][name];n=len(expected['headers'])
  actual=list(wb[name].iter_rows(min_row=1,max_row=len(expected['rows'])+1,max_col=n,values_only=True))
  assert list(actual[0])==expected['headers']
  for row,want in zip(actual[1:],expected['rows']):
   for value,reference in zip(row,want):
    if isinstance(reference,bool):reference=int(reference)
    if reference is None or reference=='':assert value is None or value==''
    elif isinstance(reference,(int,float)):assert isinstance(value,(int,float)) and math.isclose(value,reference,rel_tol=1e-12,abs_tol=1e-12),(name,value,reference)
    else:assert value==reference,(name,value,reference)
   count+=1
 for cell,expected in {'C5':238,'C6':182,'C7':141,'C8':41,'C9':56,'C10':0,'C11':546,'C12':546,'C13':546,'C14':182,'C15':525718739}.items():assert wb['Summary'][cell].value==expected
 errors=[]
 for sh in wb:
  for row in sh:
   errors.extend((sh.title,x.coordinate,x.value) for x in row if x.data_type=='e')
 assert not errors
 restore=json.loads((out/'source_restore_verification.json').read_text());assert restore==dict(restored=528,reused=0,verified=528)
 ar=json.loads((out/'source_archive_receipt.json').read_text());archive=ROOT.parent/'batch_source_deliverable'/ar['filename']
 assert digest(archive)==ar['archive_sha256'] and digest(out/'source_manifest.csv')==ar['source_manifest_sha256']
 access=json.loads((out/'source_archive_access.json').read_text());assert access['save_status']=='succeeded'
 result=dict(success=True,actual_source_files_rehashed=546,feature_rows_checked=182,clinical_status_rows_checked=238,
  workbook_data_rows_checked=count,workbook_formula_caches_checked=11,workbook_error_cells=0,
  notebook_code_cells=5,notebook_errors=0,notebook_embedded_figures_byte_identical=2,
  previous_artifacts_preserved=True,archive_restore_verified_files=528,archive_save_confirmed=True,
  model_fitted_this_step=False,external_Excel_application_tested=False)
 (out/'artifact_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
