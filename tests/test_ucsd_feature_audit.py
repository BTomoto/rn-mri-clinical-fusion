"""Tests for temporal quarantine and identity grouping, rather than model score targets."""
from pathlib import Path
import sys
import unittest
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_feature_audit import conservative_groups, observed, run, FUTURE_FIELDS


class UCSDFeatureAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=run(ROOT)
        cls.d=pd.read_csv(ROOT/'data/processed/ucsd_clinical_feature_candidates.csv').set_index('ID')

    def test_both_namespaces_are_disjoint_after_union(self):
        x=pd.DataFrame({'patient_id':['a','a','b','c'],'brats_patient_id':['x','y','x','z']})
        groups=conservative_groups(x)
        self.assertEqual(groups.nunique(),2)
        self.assertEqual(groups.iloc[0],groups.iloc[2])
        real=self.d
        self.assertTrue(real.groupby('patient_id').validation_group_conservative.nunique().eq(1).all())
        self.assertTrue(real.groupby('brats_patient_id').validation_group_conservative.nunique().eq(1).all())
        self.assertEqual(self.summary['ambiguous_mapping_timepoints'],5)
        self.assertEqual(self.summary['prior_validation_shared_brats_patients'],1)

    def test_future_and_same_day_treatments_are_not_past_exposures(self):
        self.assertTrue(pd.isna(self.d.at['UCSD-PTGBM-0145_01','conditional_days_since_last_radiation']))
        self.assertTrue(pd.isna(self.d.at['UCSD-PTGBM-0126_01','conditional_days_since_last_other_surgery']))
        self.assertTrue(pd.isna(self.d.at['UCSD-PTGBM-0001_01','conditional_days_since_last_radiation']))
        for ident in ['UCSD-PTGBM-0024_01','UCSD-PTGBM-0133_02','UCSD-PTGBM-0167_01','UCSD-PTGBM-0167_02']:
            self.assertTrue(pd.isna(self.d.at[ident,'conditional_bevacizumab_prior_strict']))
        for c in [c for c in self.d if c.startswith(('candidate_days','conditional_days'))]:
            self.assertTrue(self.d[c].dropna().gt(0).all())

    def test_unknown_zero_and_blank_remain_distinct(self):
        self.assertEqual(observed(pd.Series([None,'Unknown','Unknown or not reported',0,'No'])).tolist(),[False,False,False,True,True])
        self.assertEqual(self.summary['complete_case_examples']['plus_initial_event']['timepoints'],197)

    def test_molecular_conflicts_not_silently_filled(self):
        self.assertTrue(self.d.loc[self.d.patient_id.eq('UCSD-PTGBM-0038'),'conditional_mgmt'].isna().all())
        self.assertTrue(self.d.loc[self.d.patient_id.eq('UCSD-PTGBM-0145'),'conditional_idh'].isna().all())
        self.assertEqual(self.summary['molecular_observed']['MGMT'],149)
        self.assertEqual(self.summary['molecular_observed']['IDH'],168)

    def test_future_outcomes_are_not_candidate_columns(self):
        self.assertTrue(set(FUTURE_FIELDS).isdisjoint(self.d.columns))
        self.assertFalse(self.summary['models_fitted_this_step'])


if __name__=='__main__':unittest.main()
