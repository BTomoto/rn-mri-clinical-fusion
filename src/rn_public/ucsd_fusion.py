"""Fixed patient-grouped comparison of clinical, eight MRI, and fusion models."""
from pathlib import Path
import hashlib,importlib.metadata,json,time,warnings
import numpy as np
import pandas as pd
from scipy.optimize import brentq,minimize
from scipy.special import expit,logit
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss,roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from .ucsd_batch_features import FEATURES as MRI_FEATURES
from .ucsd_clinical_baseline import scores,sha256
from .ucsd_clinical_revalidation import prepare_cohort

SEED=20261029
CLINICAL=['age_years','log_initial_event_days','sex_male','other_treatment_prior','initial_event_missing']
FEATURES={'M0':['age_years','sex_male'],'M1':CLINICAL,'MRI':list(MRI_FEATURES),'Fusion':CLINICAL+list(MRI_FEATURES)}
EVALUATED=['M0','M1','MRI','Fusion','MRI_eroded','Fusion_eroded']
BOOT_METRICS=['roc_auc','ap_treatment_change','brier','log_loss']
PAIRS=[('Fusion','M1'),('MRI','M1'),('M1','M0'),('Fusion_eroded','M1'),('Fusion_eroded','Fusion')]
INPUTS=['data/processed/ucsd_clinical_revalidated_cohort.csv','data/processed/ucsd_clinical_image_features.csv',
 'data/processed/ucsd_image_features.csv','data/processed/ucsd_image_features_eroded.csv']


def write_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 part=path.with_name(path.name+'.partial');part.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');part.replace(path)


def prepare(root):
 root=Path(root);d=pd.read_csv(root/INPUTS[1]).sort_values('ID').reset_index(drop=True)
 original=pd.read_csv(root/INPUTS[2]);eroded=pd.read_csv(root/INPUTS[3])
 clinical,_=prepare_cohort(root)
 # The raw offset mixes Excel integers and 'Unknown'. CSV retains their text
 # representation; normalize only this audit column, never the model inputs.
 clinical['initial_event_offset_raw']=clinical.initial_event_offset_raw.astype(str)
 d['initial_event_offset_raw']=d.initial_event_offset_raw.astype(str)
 if (len(d),d.patient_id.nunique(),int(d.tumor_label.sum()))!=(182,135,141):raise ValueError('fixed_cohort_changed')
 if d.ID.duplicated().any() or original.ID.duplicated().any() or eroded.ID.duplicated().any():raise ValueError('duplicate_scan_ID')
 if set(d.ID)!=set(original.ID) or set(d.ID)!=set(eroded.ID):raise ValueError('sensitivity_case_set_mismatch')
 pd.testing.assert_frame_equal(d[clinical.columns],clinical[clinical.ID.isin(d.ID)].reset_index(drop=True))
 pd.testing.assert_frame_equal(d[['ID',*MRI_FEATURES]],original.sort_values('ID').reset_index(drop=True))
 if not np.isfinite(d[list(MRI_FEATURES)].to_numpy()).all() or not np.isfinite(eroded[list(MRI_FEATURES)].to_numpy()).all():raise ValueError('nonfinite_MRI_features')
 if d.groupby('patient_id').brats_patient_id.nunique().ne(1).any() or d.groupby('brats_patient_id').patient_id.nunique().ne(1).any():raise ValueError('identity_mapping_ambiguity')
 if d.initial_event_missing.sum()!=36 or not d.initial_event_missing.eq(d.log_initial_event_days.isna().astype(int)).all():raise ValueError('missingness_indicator_changed')
 eroded=d[['ID']].merge(eroded,on='ID',validate='one_to_one')
 return d,eroded


def freeze_plan(root):
 root=Path(root);out=root/'reports/ucsd_fusion';out.mkdir(parents=True,exist_ok=True)
 d,eroded=prepare(root);fold=np.zeros(len(d),dtype=int)
 cv=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=SEED)
 for k,(tr,te) in enumerate(cv.split(d,d.tumor_label,d.validation_group),1):
  for namespace in ['patient_id','brats_patient_id','validation_group']:
   if set(d.iloc[tr][namespace])&set(d.iloc[te][namespace]):raise ValueError('patient_overlap:'+namespace)
  if d.iloc[tr].tumor_label.nunique()!=2 or d.iloc[te].tumor_label.nunique()!=2:raise ValueError('class_missing_in_fixed_fold')
  fold[te]=k
 manifest=d[['ID','patient_id','brats_patient_id','validation_group','tumor_label']].copy();manifest['validation_fold']=fold
 lock=dict(seed=SEED,n_splits=5,protocol_sha256=sha256(root/'reports/ucsd_fusion_protocol.md'),
  analysis_code_sha256=sha256(__file__),input_sha256={p:sha256(root/p) for p in INPUTS},
  model_features=FEATURES,fold_manifest_sha256=hashlib.sha256(manifest.to_csv(index=False).encode()).hexdigest())
 path=out/'analysis_lock.json'
 if path.exists() and json.loads(path.read_text())!=lock:raise ValueError('Frozen analysis changed; preserve prior run and review explicitly')
 if (out/'cohort_and_fold_manifest.csv').exists() and (out/'cohort_and_fold_manifest.csv').read_bytes()!=manifest.to_csv(index=False).encode():raise ValueError('Frozen folds changed')
 manifest.to_csv(out/'cohort_and_fold_manifest.csv',index=False);write_json(path,lock)
 return d,eroded,manifest,lock


def make_model(name):
 if name not in FEATURES:raise ValueError('unknown_model')
 terms=[]
 if name in ['M0','M1','Fusion']:terms.append(('age',StandardScaler(),['age_years']))
 if name in ['M1','Fusion']:
  terms.append(('interval',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),['log_initial_event_days']))
 binary=['sex_male'] if name=='M0' else ['sex_male','other_treatment_prior','initial_event_missing'] if name in ['M1','Fusion'] else []
 if binary:terms.append(('binary','passthrough',binary))
 if name in ['MRI','Fusion']:terms.append(('MRI',StandardScaler(),list(MRI_FEATURES)))
 return Pipeline([('preprocess',ColumnTransformer(terms,remainder='drop')),
  ('logistic',LogisticRegression(C=1,l1_ratio=0,solver='lbfgs',max_iter=2000,tol=1e-4,class_weight=None,random_state=SEED))])


def parameters(model):
 pre=model.named_steps['preprocess'];lr=model.named_steps['logistic']
 r=dict(transformed_names=pre.get_feature_names_out().tolist(),intercept=float(lr.intercept_[0]),
  coefficients=lr.coef_[0].tolist(),iterations=int(lr.n_iter_[0]),classes=lr.classes_.tolist(),continuous={},binary=[])
 for name,transformer,columns in pre.transformers_:
  if name=='remainder':continue
  if name=='binary':r['binary']=list(columns);continue
  scale=transformer.named_steps['scale'] if name=='interval' else transformer
  r['continuous'][name]=dict(columns=list(columns),mean=scale.mean_.tolist(),scale=scale.scale_.tolist())
  if name=='interval':r['continuous'][name]['impute_median']=float(transformer.named_steps['impute'].statistics_[0])
 return r


def fit(model,d):
 with warnings.catch_warnings():
  warnings.simplefilter('error',ConvergenceWarning);model.fit(d,d.tumor_label)
 return model


def evaluate(y,p):
 y=np.asarray(y);p=np.asarray(p)
 r=scores(y,p);tn,fp,fn,tp=[r[k] for k in ['tn','fp','fn','tp']]
 r.update(log_loss=float(log_loss(y,p,labels=[0,1])),
  precision_tumor=None if tp+fp==0 else float(tp/(tp+fp)),
  precision_treatment_change=None if tn+fn==0 else float(tn/(tn+fn)))
 return r


def grouped_oof(d,eroded,manifest):
 pred=d[['ID','patient_id','brats_patient_id','validation_group','tumor_label']].merge(manifest[['ID','validation_fold']],on='ID',validate='one_to_one')
 for name in [*EVALUATED,'prior']:pred[name+'_oof_probability']=np.nan
 records=[]
 for fold in range(1,6):
  tr=np.flatnonzero(pred.validation_fold.ne(fold));te=np.flatnonzero(pred.validation_fold.eq(fold))
  train,test=d.iloc[tr],d.iloc[te];record=dict(fold=fold,train_IDs=train.ID.tolist(),test_IDs=test.ID.tolist(),
   n_train=len(tr),n_test=len(te),n_test_patients=int(test.patient_id.nunique()),
   test_tumor=int(test.tumor_label.sum()),test_treatment_change=int(test.tumor_label.eq(0).sum()),
   train_interval_observed=int(train.log_initial_event_days.notna().sum()),models={})
  for key in ['patient_id','brats_patient_id','validation_group']:
   overlap=set(train[key])&set(test[key]);record[key+'_overlap']=len(overlap)
   if overlap:raise ValueError('validation_patient_leakage')
  for name in EVALUATED:
   base=name.removesuffix('_eroded');xx=d.copy()
   if name.endswith('_eroded'):xx.loc[:,list(MRI_FEATURES)]=eroded[list(MRI_FEATURES)].to_numpy()
   model=fit(make_model(base),xx.iloc[tr]);prob=model.predict_proba(xx.iloc[te])[:,1]
   pred.loc[te,name+'_oof_probability']=prob
   record['models'][name]=dict(parameters=parameters(model),metrics=evaluate(test.tumor_label,prob))
  prior=float(train.tumor_label.mean());pred.loc[te,'prior_oof_probability']=prior;record['train_tumor_prevalence']=prior
  records.append(record)
 for name in [*EVALUATED,'prior']:
  p=pred[name+'_oof_probability']
  if p.isna().any() or not p.between(0,1).all():raise ValueError('incomplete_OOF_predictions')
  pred[name+'_prediction_0_5']=p.ge(.5).astype(int)
 return pred,records


def metric_vector(y,p):
 return [float(roc_auc_score(y,p)),float(average_precision_score(1-y,1-p)),float(brier_score_loss(y,p)),float(log_loss(y,p,labels=[0,1]))]


def paired_bootstrap(d,n=2000,progress=False):
 rng=np.random.default_rng(SEED+1);clusters=[np.asarray(v) for v in d.groupby('validation_group',sort=True).indices.values()]
 y=d.tumor_label.to_numpy();ps={name:d[name+'_oof_probability'].to_numpy() for name in EVALUATED}
 columns=[f'{name}__{metric}' for name in EVALUATED for metric in BOOT_METRICS]
 columns += [f'{a}_minus_{b}__{metric}' for a,b in PAIRS for metric in BOOT_METRICS]
 draws=[];skipped=0
 for k in range(n):
  ix=np.concatenate([clusters[j] for j in rng.integers(0,len(clusters),len(clusters))]);yy=y[ix]
  if np.unique(yy).size<2:skipped+=1;continue
  vals={name:metric_vector(yy,p[ix]) for name,p in ps.items()}
  row=[k+1,len(ix),*list(v for name in EVALUATED for v in vals[name])]
  row += [vals[a][i]-vals[b][i] for a,b in PAIRS for i in range(len(BOOT_METRICS))]
  draws.append(row)
  if progress and (k+1)%250==0:print(f'Paired patient bootstrap {k+1}/{n}',flush=True)
 if len(draws)<.95*n:raise ValueError('bootstrap_valid_rate_below_95_percent')
 frame=pd.DataFrame(draws,columns=['draw','resampled_scan_count',*columns]);quant=frame[columns].quantile([.025,.975])
 intervals={key:dict(lower=float(quant.loc[.025,key]),upper=float(quant.loc[.975,key])) for key in columns}
 return intervals,frame,skipped


def calibration_diagnostics(y,p):
 """Diagnostics fitted to OOF predictions, never returned as recalibrated predictions."""
 y=np.asarray(y);p=np.asarray(p);z=logit(np.clip(p,np.finfo(float).eps,1-np.finfo(float).eps))
 r=dict(calibration_intercept_offset=None,calibration_joint_intercept=None,calibration_slope=None,error=None)
 try:
  offset=brentq(lambda a:np.sum(expit(z+a)-y),-80,80)
  x=np.column_stack([np.ones(len(y)),z])
  def objective(beta):
   eta=x@beta;return float(np.sum(np.logaddexp(0,eta)-y*eta)),x.T@(expit(eta)-y)
  opt=minimize(objective,np.array([0.,1.]),jac=True,method='L-BFGS-B',options=dict(maxiter=2000,gtol=1e-9,ftol=1e-13))
  pfit=expit(x@opt.x);h=x.T@((pfit*(1-pfit))[:,None]*x)
  if not (opt.success or np.max(np.abs(opt.jac))<1e-5) or np.linalg.eigvalsh(h).min()<1e-8:raise ValueError('calibration_fit_failed_or_separated')
  r.update(calibration_intercept_offset=float(offset),calibration_joint_intercept=float(opt.x[0]),calibration_slope=float(opt.x[1]))
 except Exception as exc:r['error']=type(exc).__name__+': '+str(exc)
 bins=pd.qcut(pd.Series(p),5,duplicates='drop');frame=pd.DataFrame(dict(y=y,p=p,bin=bins))
 rows=[]
 for k,(_,g) in enumerate(frame.groupby('bin',observed=True),1):
  rows.append(dict(bin=k,n=len(g),mean_predicted=float(g.p.mean()),observed_tumor=float(g.y.mean()),tumor_count=int(g.y.sum())))
 return r,rows


def run(root,n_bootstrap=2000):
 if n_bootstrap!=2000:raise ValueError('Production protocol fixes 2000 bootstrap draws')
 start=time.monotonic();root=Path(root);out=root/'reports/ucsd_fusion'
 d,eroded,manifest,lock=freeze_plan(root)
 pred,folds=grouped_oof(d,eroded,manifest);pred.to_csv(root/'data/processed/ucsd_fusion_oof.csv',index=False)
 write_json(out/'fold_audit.json',folds)
 metrics={name:evaluate(pred.tumor_label,pred[name+'_oof_probability']) for name in [*EVALUATED,'prior']}
 intervals,draws,skipped=paired_bootstrap(pred,n_bootstrap,progress=True);draws.to_csv(out/'paired_patient_bootstrap.csv',index=False)
 calibration={};bins=[]
 for name in EVALUATED:
  diag,rows=calibration_diagnostics(pred.tumor_label,pred[name+'_oof_probability']);calibration[name]=diag
  bins.extend(dict(model=name,**row) for row in rows)
 pd.DataFrame(bins).to_csv(out/'calibration_bins.csv',index=False)
 final={name:parameters(fit(make_model(name),d)) for name in FEATURES}
 metrics_rows=[]
 for name in [*EVALUATED,'prior']:
  row=dict(model=name,**metrics[name],**calibration.get(name,{}))
  for metric in BOOT_METRICS:
   if name=='prior':continue
   row[metric+'_ci_lower']=intervals[name+'__'+metric]['lower'];row[metric+'_ci_upper']=intervals[name+'__'+metric]['upper']
  metrics_rows.append(row)
 pd.DataFrame(metrics_rows).to_csv(out/'model_metrics.csv',index=False)
 comparisons=[]
 for a,b in PAIRS:
  for metric in BOOT_METRICS:
   comparisons.append(dict(comparison=a+'_minus_'+b,metric=metric,difference=metrics[a][metric]-metrics[b][metric],
    **intervals[a+'_minus_'+b+'__'+metric],primary_comparison=a=='Fusion' and b=='M1' and metric=='roc_auc'))
 pd.DataFrame(comparisons).to_csv(out/'paired_comparisons.csv',index=False)
 fold_rows=[]
 for f in folds:
  for name,model in f['models'].items():
   fold_rows.append(dict(fold=f['fold'],model=name,n_train=f['n_train'],n_test=f['n_test'],n_test_patients=f['n_test_patients'],test_tumor=f['test_tumor'],test_treatment_change=f['test_treatment_change'],**model['metrics']))
 pd.DataFrame(fold_rows).to_csv(out/'fold_metrics.csv',index=False)
 coeff=[]
 for name,p in final.items():
  for term,value in zip(p['transformed_names'],p['coefficients']):coeff.append(dict(model=name,term=term,coefficient=value,fit='full_cohort_descriptive_not_validation'))
 pd.DataFrame(coeff).to_csv(out/'full_fit_coefficients.csv',index=False)
 summary=dict(step=18,date='2026-10-29',scans=len(d),source_patients=int(d.patient_id.nunique()),validation_groups=int(d.validation_group.nunique()),
  tumor_scans=int(d.tumor_label.sum()),treatment_change_scans=int(d.tumor_label.eq(0).sum()),interval_missing_scans=int(d.initial_event_missing.sum()),
  models=FEATURES,metrics=metrics,calibration=calibration,patient_cluster_bootstrap_95ci=intervals,paired_comparisons=comparisons,
  bootstrap_attempts=n_bootstrap,bootstrap_valid=len(draws),bootstrap_one_class_skipped=skipped,bootstrap_models_refitted=False,
  uncertainty_limit='Patient resampling conditional on fixed OOF predictions; excludes full training/split variability',
  n_splits=5,seed=SEED,C=1,class_weight=None,threshold=.5,hyperparameter_search=False,feature_selection=False,
  same_cases_and_folds=True,patient_overlap=0,brats_patient_overlap=0,full_fit_parameters=final,full_fit_training_metrics_reported=False,
  independent_external_validation=False,source_annotation_blinding_confirmed=False,physical_scale_confirmed=False,
  input_and_protocol_lock=lock,versions={p:importlib.metadata.version(p) for p in ['scikit-learn','numpy','pandas','scipy','matplotlib']},
  elapsed_seconds=round(time.monotonic()-start,3),next_step_requires_user_approval=True)
 write_json(out/'metrics.json',summary);return summary
