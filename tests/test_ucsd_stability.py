"""Guard fixed repeat plans, non-outcome scan selection and failure visibility."""
from pathlib import Path
import sys,unittest
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_stability import (freeze_plan,select_single,grouped_oof,
 summary_distribution,single_bootstrap,MODELS,SEEDS)


class StabilityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d,cls.s,cls.m,cls.plans,cls.sm,cls.sp,cls.lock=freeze_plan(ROOT)

 def test_all_fixed_repeats_preserve_two_patient_namespaces(self):
  self.assertEqual(list(SEEDS),list(range(20261029,20261049)))
  self.assertEqual(len(self.m),3640)
  for _,m in self.m.groupby('repeat'):
   self.assertEqual(m.ID.nunique(),182)
   for key in ['patient_id','brats_patient_id','validation_group']:self.assertTrue(m.groupby(key).validation_fold.nunique().eq(1).all())
  self.assertTrue(all(f['valid'] for p in self.plans for f in p['folds']))

 def test_single_scan_rule_is_independent_of_outcome_and_image_values(self):
  altered=self.d.copy();altered['tumor_label']=1-altered.tumor_label
  for c in [x for x in altered if x.startswith(('FLAIR_','T1post_'))]:altered[c]=99999
  a,_=select_single(altered.sample(frac=1,random_state=42))
  self.assertEqual(a.ID.tolist(),self.s.ID.tolist());self.assertEqual(len(a),135)
  self.assertFalse(a.patient_id.duplicated().any());self.assertFalse(a.brats_patient_id.duplicated().any())
  _,ledger=select_single(self.d)
  self.assertEqual(ledger.selected.sum(),135);self.assertEqual(len(ledger),182)
  selected_sessions=ledger[ledger.selected].set_index('patient_id').session_number
  self.assertTrue(selected_sessions.sort_index().eq(ledger.groupby('patient_id').session_number.min().sort_index()).all())

 def test_first_repeat_exactly_preserves_stage18_folds(self):
  prior=pd.read_csv(ROOT/'reports/ucsd_fusion/cohort_and_fold_manifest.csv').set_index('ID')
  first=self.m[self.m['repeat'].eq(1)].set_index('ID')
  np.testing.assert_array_equal(first.validation_fold,prior.loc[first.index].validation_fold)

 def test_invalid_folds_are_visible_and_never_filled_with_zero_predictions(self):
  broken=[{**f,'valid':False,'errors':['deliberate_class_failure_test']} for f in self.sp]
  pred,records,metrics,errors,complete=grouped_oof(self.s,self.sm,broken)
  self.assertFalse(complete);self.assertEqual(len(errors),5);self.assertFalse(metrics)
  self.assertTrue(pred.filter(like='_oof_probability').isna().all().all())

 def test_split_distribution_is_descriptive_and_preserves_metric_identity(self):
  x=pd.DataFrame(dict(comparison=['Fusion_minus_M1']*3,metric=['roc_auc']*3,difference=[-.2,.1,.4]))
  row=summary_distribution(x,['comparison','metric'],['difference']).iloc[0]
  self.assertEqual(row.metric,'roc_auc');self.assertEqual(row.statistic,'difference')
  self.assertAlmostEqual(row['median'],.1);self.assertEqual(row.positive_count,2)
  self.assertEqual(row.interpretation,'descriptive_split_distribution_not_confidence_interval')

 def test_patient_paired_single_scan_bootstrap_zero_for_identical_predictions(self):
  p=self.s[['validation_group','tumor_label']].copy()
  for name in MODELS:p[name+'_oof_probability']=np.linspace(.1,.95,len(p))
  ci,draws,skipped=single_bootstrap(p,n=25)
  self.assertEqual(len(draws)+skipped,25)
  for key in ci:
   if '_minus_' in key:self.assertEqual(ci[key],dict(lower=0.,upper=0.))


if __name__=='__main__':unittest.main()
