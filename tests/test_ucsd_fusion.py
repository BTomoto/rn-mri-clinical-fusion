"""Guard leakage, paired uncertainty and calibration definitions in Stage18."""
from pathlib import Path
import sys,unittest
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_fusion import (FEATURES,MRI_FEATURES,EVALUATED,freeze_plan,make_model,parameters,
 grouped_oof,paired_bootstrap,calibration_diagnostics,evaluate)


class FusionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d,cls.e,cls.manifest,cls.lock=freeze_plan(ROOT)

 def test_two_patient_namespaces_and_fixed_case_set(self):
  self.assertEqual((len(self.d),self.d.patient_id.nunique()),(182,135))
  self.assertEqual(self.d.ID.tolist(),self.e.ID.tolist())
  for key in ['patient_id','brats_patient_id','validation_group']:
   self.assertTrue(self.manifest.groupby(key).validation_fold.nunique().eq(1).all())
  self.assertEqual({k:len(v) for k,v in FEATURES.items()},{'M0':2,'M1':5,'MRI':8,'Fusion':13})

 def test_fold_preprocessing_is_training_only_and_frozen_at_prediction(self):
  d=self.d;m=self.manifest;tr=d[m.validation_fold.ne(1)];te=d[m.validation_fold.eq(1)].copy()
  model=make_model('Fusion').fit(tr,tr.tumor_label);before=parameters(model)
  self.assertAlmostEqual(before['continuous']['interval']['impute_median'],np.nanmedian(tr.log_initial_event_days))
  np.testing.assert_allclose(before['continuous']['MRI']['mean'],tr[list(MRI_FEATURES)].mean())
  te.loc[:,list(MRI_FEATURES)]=1e6;te['log_initial_event_days']=1e6;model.predict_proba(te)
  self.assertEqual(before,parameters(model))

 def test_outcome_and_future_columns_cannot_enter_predictions(self):
  model=make_model('Fusion').fit(self.d,self.d.tumor_label);altered=self.d.copy()
  altered['tumor_label']=1-altered.tumor_label;altered['future_survival']=99999
  altered['ID']='fake';altered['TCT_volume']=9999;altered['label_source']='fake'
  np.testing.assert_array_equal(model.predict_proba(self.d),model.predict_proba(altered))

 def test_pairwise_bootstrap_zero_when_probabilities_identical(self):
  d=self.d[['validation_group','tumor_label']].copy();p=np.linspace(.1,.95,len(d))
  for name in EVALUATED:d[name+'_oof_probability']=p
  ci,draws,skip=paired_bootstrap(d,n=25)
  for key in ci:
   if '_minus_' in key:self.assertEqual(ci[key],dict(lower=0.,upper=0.))
  self.assertTrue(draws.filter(like='_minus_').eq(0).all().all());self.assertEqual(len(draws)+skip,25)

 def test_calibration_and_rare_class_direction_by_hand(self):
  p=np.repeat([.2,.4,.6,.8],10);y=np.concatenate([np.r_[np.ones(k),np.zeros(10-k)] for k in [2,4,6,8]])
  r,bins=calibration_diagnostics(y,p)
  self.assertIsNone(r['error']);self.assertAlmostEqual(r['calibration_slope'],1.,places=6)
  self.assertAlmostEqual(r['calibration_intercept_offset'],0.,places=6);self.assertEqual(sum(b['n'] for b in bins),40)
  s=evaluate(np.array([0,0,1,1]),np.array([.2,.8,.3,.9]))
  self.assertEqual([s[k] for k in ['tn','fp','fn','tp']],[1,1,1,1])
  self.assertEqual(s['specificity_treatment_change'],.5)

 def test_every_model_uses_exact_same_held_out_cases(self):
  pred,folds=grouped_oof(self.d,self.e,self.manifest)
  self.assertEqual(len(pred),182)
  for name in [*EVALUATED,'prior']:self.assertTrue(pred[name+'_oof_probability'].between(0,1).all())
  for f in folds:
   self.assertEqual(set(f['models']),set(EVALUATED));self.assertEqual(f['patient_id_overlap']+f['brats_patient_id_overlap'],0)
   te=pred[pred.validation_fold.eq(f['fold'])];tr=pred[pred.validation_fold.ne(f['fold'])]
   np.testing.assert_allclose(te.prior_oof_probability,tr.tumor_label.mean())
   self.assertEqual(set(te.ID),set(f['test_IDs']))


if __name__=='__main__':unittest.main()
