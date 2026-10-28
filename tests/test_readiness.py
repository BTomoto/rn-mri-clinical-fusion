import unittest
import sys
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.readiness import outcome_class,mask_labels_to_lesion


class ReadinessTests(unittest.TestCase):
    def test_missing_endpoint_never_becomes_non_event(self):
        self.assertEqual(outcome_class(float('nan'),100),'unknown')
        self.assertEqual(outcome_class(float('nan'),float('nan')),'unknown')

    def test_treatment_order_boundaries(self):
        self.assertEqual(outcome_class(100,100),'rn_at_or_before_index_srs')
        self.assertEqual(outcome_class(99,100),'rn_at_or_before_index_srs')
        self.assertEqual(outcome_class(101,100),'recorded_rn_after_index_srs')
        self.assertEqual(outcome_class(101,float('nan')),'recorded_rn_no_index_srs')

    def test_mask_encoding_does_not_return_diagnosis(self):
        self.assertEqual(mask_labels_to_lesion(11),(1,1))
        self.assertEqual(mask_labels_to_lesion(92),(9,2))
        with self.assertRaises(ValueError):mask_labels_to_lesion(13)

    def test_audit_preserves_source_and_unknowns(self):
        a=pd.read_csv(ROOT/'data/processed/outcome_timing_audit.csv')
        s=pd.read_csv(ROOT/'data/processed/lesions.csv')
        j=a.merge(s,on='lesion_key',validate='one_to_one',suffixes=('_audit','_source'))
        pd.testing.assert_series_equal(j.rn_time_day_audit,j.rn_time_day_source,check_names=False)
        self.assertTrue((j.loc[j.rn_time_day_source.isna(),'rn_evidence_class']=='unknown').all())
        self.assertEqual(a.verified_non_event.sum(),0)
        self.assertEqual(a.final_eligible.sum(),0)

    def test_mask_based_baseline_retains_mixed_morphology_date_case(self):
        f=pd.read_csv(ROOT/'data/processed/baseline_existing_features.csv')
        self.assertEqual(f.lesion_key.nunique(),len(f))
        self.assertIn('40001_L2',set(f.lesion_key))
        self.assertEqual(f.use_for_model.sum(),0)
        origin=pd.Timestamp('1900-01-01')
        days=(pd.to_datetime(f.Timepoint.astype(str),format='%Y%m%d')-origin).dt.days
        self.assertTrue(((days < f.first_srs_start_day)&(days >= f.first_srs_start_day-30)).all())
        self.assertTrue(f.loc[f.rn_time_day.isna(),'rn_evidence_class'].eq('unknown').all())


if __name__=='__main__':unittest.main()
