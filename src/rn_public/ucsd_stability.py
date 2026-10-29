"""Prespecified split stability and one available scan per patient; no tuning."""
from pathlib import Path
import hashlib,json,time
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from .ucsd_fusion import (prepare,make_model,fit,parameters,evaluate,calibration_diagnostics,
                         metric_vector,BOOT_METRICS,INPUTS,FEATURES,write_json)
from .ucsd_clinical_baseline import sha256

SEEDS=tuple(range(20261029,20261049))
MODELS=tuple(FEATURES)
KEYS=['roc_auc','ap_treatment_change','brier','log_loss']


def select_single(d):
 d=d.copy()
 if d.ID.duplicated().any() or not d.ID.str.fullmatch(r'UCSD-PTGBM-\d{4}_\d{2}').all():raise ValueError('invalid_or_duplicate_scan_ID')
 d['session_number']=d.ID.str.rsplit('_',n=1).str[1].astype(int)
 ordered=d.sort_values(['patient_id','session_number','ID'])
 chosen=set(ordered.drop_duplicates('patient_id').ID)
 ledger=d[['ID','patient_id','brats_patient_id','validation_group','tumor_label','session_number']].copy()
 ledger['selected']=ledger.ID.isin(chosen)
 ledger['reason']=np.where(ledger.selected,'minimum_numeric_session_in_current_imaged_subset','later_available_session_excluded_for_single_scan_sensitivity')
 selected=d[d.ID.isin(chosen)].drop(columns='session_number').sort_values('ID').reset_index(drop=True)
 if selected.patient_id.duplicated().any() or selected.brats_patient_id.duplicated().any():raise ValueError('single_scan_patient_mapping_ambiguous')
 return selected,ledger.sort_values('ID').reset_index(drop=True)


def split_plan(d,seed):
 fold=np.zeros(len(d),dtype=int);records=[]
 cv=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=seed)
 for k,(tr,te) in enumerate(cv.split(d,d.tumor_label,d.validation_group),1):
  train,test=d.iloc[tr],d.iloc[te];errors=[]
  for key in ['patient_id','brats_patient_id','validation_group']:
   if set(train[key])&set(test[key]):errors.append('patient_overlap:'+key)
  if train.tumor_label.nunique()!=2 or test.tumor_label.nunique()!=2:errors.append('class_missing_in_train_or_validation')
  records.append(dict(fold=k,n_train=len(tr),n_test=len(te),train_patients=int(train.patient_id.nunique()),
   test_patients=int(test.patient_id.nunique()),train_tumor=int(train.tumor_label.sum()),test_tumor=int(test.tumor_label.sum()),
   test_treatment_change=int(test.tumor_label.eq(0).sum()),train_IDs=train.ID.tolist(),test_IDs=test.ID.tolist(),valid=not errors,errors=errors))
  fold[te]=k
 manifest=d[['ID','patient_id','brats_patient_id','validation_group','tumor_label']].copy();manifest['validation_fold']=fold
 return manifest,records


def freeze_plan(root):
 root=Path(root);out=root/'reports/ucsd_stability';out.mkdir(parents=True,exist_ok=True)
 old=json.loads((root/'reports/ucsd_fusion/analysis_lock.json').read_text())
 if sha256(root/'src/rn_public/ucsd_fusion.py')!=old['analysis_code_sha256']:raise ValueError('Stage18_model_code_changed')
 for p,h in old['input_sha256'].items():
  if sha256(root/p)!=h:raise ValueError('Stage18_source_input_changed:'+p)
 d,_=prepare(root);single,ledger=select_single(d)
 if len(single)!=135:raise ValueError('fixed_single_scan_patient_count_changed')
 manifests=[];plans=[]
 for repeat,seed in enumerate(SEEDS,1):
  m,p=split_plan(d,seed);m.insert(0,'seed',seed);m.insert(0,'repeat',repeat);manifests.append(m)
  plans.append(dict(repeat=repeat,seed=seed,folds=p))
 full_manifest=pd.concat(manifests,ignore_index=True);single_manifest,single_plan=split_plan(single,SEEDS[0])
 files={'repeated_fold_manifest.csv':full_manifest.to_csv(index=False).encode(),
        'single_scan_selection.csv':ledger.to_csv(index=False).encode(),
        'single_scan_fold_manifest.csv':single_manifest.to_csv(index=False).encode()}
 pin=[*INPUTS,'reports/ucsd_fusion/analysis_lock.json','reports/ucsd_fusion/metrics.json','data/processed/ucsd_fusion_oof.csv']
 lock=dict(protocol_sha256=sha256(root/'reports/ucsd_stability_protocol.md'),analysis_code_sha256=sha256(__file__),
  prior_model_code_sha256=old['analysis_code_sha256'],input_sha256={p:sha256(root/p) for p in pin},
  seeds=list(SEEDS),single_scan_seed=SEEDS[0],single_scan_bootstrap_seed=20261101,
  single_scan_rule='minimum_numeric_session_within_current_imaged_subset_then_ID',models=FEATURES,
  manifest_sha256={p:hashlib.sha256(b).hexdigest() for p,b in files.items()})
 path=out/'analysis_lock.json'
 if path.exists() and json.loads(path.read_text())!=lock:raise ValueError('Frozen_stage19_analysis_changed')
 for name,data in files.items():
  path=out/name
  if path.exists() and path.read_bytes()!=data:raise ValueError('Frozen_stage19_manifest_changed:'+name)
  path.write_bytes(data)
 write_json(out/'analysis_lock.json',lock)
 return d,single,full_manifest,plans,single_manifest,single_plan,lock


def grouped_oof(d,manifest,plan):
 pred=manifest.copy();records=[];errors=[]
 for name in MODELS:pred[name+'_oof_probability']=np.nan
 for f in plan:
  record=dict(**f,models={})
  if not f['valid']:
   errors.append(dict(fold=f['fold'],model=None,error='invalid_frozen_fold:'+','.join(f['errors'])));records.append(record);continue
  tr=d[d.ID.isin(f['train_IDs'])];te=d[d.ID.isin(f['test_IDs'])]
  for name in MODELS:
   try:
    model=fit(make_model(name),tr);prob=model.predict_proba(te)[:,1]
    if not np.isfinite(prob).all() or ((prob<0)|(prob>1)).any():raise ValueError('invalid_probability')
    mapping=dict(zip(te.ID,prob));ix=pred.ID.isin(te.ID);pred.loc[ix,name+'_oof_probability']=pred.loc[ix,'ID'].map(mapping)
    record['models'][name]=dict(success=True,parameters=parameters(model),metrics=evaluate(te.tumor_label,prob))
   except Exception as exc:
    error=type(exc).__name__+': '+str(exc);record['models'][name]=dict(success=False,error=error)
    errors.append(dict(fold=f['fold'],model=name,error=error))
  records.append(record)
 complete=not errors and not pred.filter(like='_oof_probability').isna().any().any()
 metrics=[]
 for name in MODELS:
  p=pred[name+'_oof_probability'];pred[name+'_prediction_0_5']=np.where(p.isna(),np.nan,p.ge(.5).astype(float))
  if complete:
   diag,_=calibration_diagnostics(pred.tumor_label,p)
   metrics.append(dict(model=name,**evaluate(pred.tumor_label,p),**diag))
 return pred,records,metrics,errors,complete


def summary_distribution(frame,group_columns,metric_columns):
 rows=[]
 for keys,g in frame.groupby(group_columns,sort=False,dropna=False):
  if not isinstance(keys,tuple):keys=(keys,)
  for metric in metric_columns:
   values=g[metric].dropna()
   identity=dict(zip(group_columns,keys));identity['statistic' if 'metric' in identity else 'metric']=metric
   rows.append(dict(**identity,n_complete=len(values),median=None if values.empty else float(values.median()),
    q25=None if values.empty else float(values.quantile(.25)),q75=None if values.empty else float(values.quantile(.75)),
    minimum=None if values.empty else float(values.min()),maximum=None if values.empty else float(values.max()),
    positive_count=int(values.gt(0).sum()),zero_count=int(values.eq(0).sum()),negative_count=int(values.lt(0).sum()),
    interpretation='descriptive_split_distribution_not_confidence_interval'))
 return pd.DataFrame(rows)


def single_bootstrap(pred,n=2000):
 rng=np.random.default_rng(20261101);clusters=[np.asarray(x) for x in pred.groupby('validation_group',sort=True).indices.values()]
 y=pred.tumor_label.to_numpy();ps={name:pred[name+'_oof_probability'].to_numpy() for name in MODELS}
 columns=[f'{name}__{k}' for name in MODELS for k in BOOT_METRICS]+['Fusion_minus_M1__'+k for k in BOOT_METRICS]
 rows=[];skipped=0
 for i in range(n):
  ix=np.concatenate([clusters[j] for j in rng.integers(0,len(clusters),len(clusters))]);yy=y[ix]
  if np.unique(yy).size<2:skipped+=1;continue
  vals={name:metric_vector(yy,p[ix]) for name,p in ps.items()}
  rows.append([i+1,*[v for name in MODELS for v in vals[name]],*[vals['Fusion'][j]-vals['M1'][j] for j in range(len(BOOT_METRICS))]])
 if len(rows)<.95*n:raise ValueError('single_scan_bootstrap_valid_rate_below_95_percent')
 draws=pd.DataFrame(rows,columns=['draw',*columns]);q=draws[columns].quantile([.025,.975])
 return {k:dict(lower=float(q.loc[.025,k]),upper=float(q.loc[.975,k])) for k in columns},draws,skipped


def run(root):
 start=time.monotonic();root=Path(root);out=root/'reports/ucsd_stability'
 d,single,manifest,plans,sm,sp,lock=freeze_plan(root)
 predictions=[];metric_rows=[];deltas=[];statuses=[];all_errors=[];fold_rows=[]
 for p in plans:
  repeat,seed=p['repeat'],p['seed'];m=manifest[manifest['repeat'].eq(repeat)].drop(columns=['repeat','seed']).reset_index(drop=True)
  pred,records,metrics,errors,complete=grouped_oof(d,m,p['folds'])
  pred.insert(0,'seed',seed);pred.insert(0,'repeat',repeat);predictions.append(pred)
  write_json(out/f'repeated_fold_audits/repeat_{repeat:02d}.json',dict(repeat=repeat,seed=seed,complete=complete,errors=errors,folds=records))
  statuses.append(dict(repeat=repeat,seed=seed,complete=complete,failed_fold_model_records=len(errors)))
  all_errors.extend(dict(analysis='repeated',repeat=repeat,seed=seed,**e) for e in errors)
  metric_rows.extend(dict(repeat=repeat,seed=seed,**v) for v in metrics)
  if complete:
   by={x['model']:x for x in metrics};deltas.extend(dict(repeat=repeat,seed=seed,comparison='Fusion_minus_M1',metric=k,difference=by['Fusion'][k]-by['M1'][k]) for k in KEYS)
  for f in records:
   for name,v in f['models'].items():
    fold_rows.append(dict(repeat=repeat,seed=seed,fold=f['fold'],model=name,n_train=f['n_train'],n_test=f['n_test'],test_patients=f['test_patients'],test_tumor=f['test_tumor'],test_treatment_change=f['test_treatment_change'],success=v['success'],**v.get('metrics',{}),error=v.get('error')))
  print(f'Repeated patient-grouped validation {repeat}/{len(SEEDS)}; complete={complete}',flush=True)
 repeated=pd.concat(predictions,ignore_index=True);repeated.to_csv(root/'data/processed/ucsd_stability_repeated_oof.csv',index=False)
 metric_frame=pd.DataFrame(metric_rows);delta_frame=pd.DataFrame(deltas)
 metric_frame.to_csv(out/'repeated_metrics.csv',index=False);delta_frame.to_csv(out/'repeated_paired_differences.csv',index=False)
 pd.DataFrame(fold_rows).to_csv(out/'repeated_fold_metrics.csv',index=False);pd.DataFrame(statuses).to_csv(out/'repeat_status.csv',index=False)
 distribution=summary_distribution(metric_frame,['model'],[*KEYS,'specificity_treatment_change','sensitivity_tumor','balanced_accuracy','calibration_slope'])
 distribution.to_csv(out/'repeated_metric_distribution.csv',index=False)
 delta_distribution=summary_distribution(delta_frame,['comparison','metric'],['difference']);delta_distribution.to_csv(out/'repeated_delta_distribution.csv',index=False)
 anchor=json.loads((root/'reports/ucsd_fusion/metrics.json').read_text());prior=pd.read_csv(root/'data/processed/ucsd_fusion_oof.csv').set_index('ID')
 first=repeated[repeated['repeat'].eq(1)].set_index('ID');anchor_difference=0.
 for name in MODELS:
  x=first[name+'_oof_probability'].to_numpy();expected=prior.loc[first.index,name+'_oof_probability'].to_numpy()
  if not np.isfinite(x).all() or not np.allclose(x,expected,atol=1e-12,rtol=1e-12):raise ValueError('Stage18_anchor_reproduction_failed')
  anchor_difference=max(anchor_difference,float(np.max(np.abs(x-expected))))
 pred,records,smetrics,errors,scomplete=grouped_oof(single,sm,sp)
 pred.to_csv(root/'data/processed/ucsd_stability_single_scan_oof.csv',index=False)
 write_json(out/'single_scan_fold_audit.json',dict(complete=scomplete,errors=errors,folds=records))
 all_errors.extend(dict(analysis='single_scan',repeat=None,seed=SEEDS[0],**e) for e in errors)
 single_info=dict(scans=len(single),patients=int(single.patient_id.nunique()),tumor_scans=int(single.tumor_label.sum()),
  treatment_change_scans=int(single.tumor_label.eq(0).sum()),interval_missing_scans=int(single.initial_event_missing.sum()),complete=scomplete,
  metrics={},paired_differences={},bootstrap_valid=0,bootstrap_skipped=None,bootstrap_95ci={})
 if scomplete:
  ci,draws,skip=single_bootstrap(pred);draws.to_csv(out/'single_scan_patient_bootstrap.csv',index=False)
  for row in smetrics:
   for k in BOOT_METRICS:row[k+'_ci_lower']=ci[row['model']+'__'+k]['lower'];row[k+'_ci_upper']=ci[row['model']+'__'+k]['upper']
  single_info.update(metrics={x['model']:x for x in smetrics},paired_differences={k:next(x for x in smetrics if x['model']=='Fusion')[k]-next(x for x in smetrics if x['model']=='M1')[k] for k in KEYS},bootstrap_valid=len(draws),bootstrap_skipped=skip,bootstrap_95ci=ci)
 pd.DataFrame(smetrics).to_csv(out/'single_scan_metrics.csv',index=False)
 write_json(out/'failures.json',dict(records=all_errors))
 summary=dict(step=19,date='2026-10-29',scans=len(d),source_patients=int(d.patient_id.nunique()),repeats_requested=len(SEEDS),
  repeats_complete=sum(s['complete'] for s in statuses),repeats_failed=sum(not s['complete'] for s in statuses),
  model_fold_failure_records=len(all_errors),models=FEATURES,seeds=list(SEEDS),repeated_metric_distribution=distribution.to_dict('records'),
  repeated_primary_difference_distribution=delta_distribution.to_dict('records'),anchor_maximum_probability_difference=anchor_difference,
  single_scan=single_info,hyperparameter_search=False,feature_selection=False,threshold_optimization=False,
  repeats_are_independent_samples=False,repeated_ranges_are_confidence_intervals=False,probability_ensemble_created=False,
  bootstrap_models_refitted=False,external_validation=False,prior_primary_analysis_replaced=False,
  input_and_protocol_lock=lock,elapsed_seconds=round(time.monotonic()-start,3),next_step_requires_user_approval=True)
 write_json(out/'metrics.json',summary);return summary
