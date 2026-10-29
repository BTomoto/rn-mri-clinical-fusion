"""Regression checks for the actual identity/temporal failure modes found in this project."""
from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_clinical_revalidation import prepare_cohort,grouped_oof,make_model,parameter_record,paired_intervals,EXCLUDED_IDS


class ClinicalRevalidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d,cls.excluded=prepare_cohort(ROOT)
        cls.pred,cls.folds=grouped_oof(cls.d)

    def test_quarantine_preserves_the_other_scans_and_labels(self):
        self.assertEqual(sorted(self.excluded.ID),EXCLUDED_IDS)
        self.assertEqual((len(self.d),self.d.patient_id.nunique(),self.d.tumor_label.sum()),(238,176,187))
        self.assertTrue(set(self.d.ID).isdisjoint(EXCLUDED_IDS))
        self.assertEqual(self.d.initial_event_missing.sum(),46)
        self.assertTrue(self.d.days_since_initial_event.dropna().gt(0).all())

    def test_both_namespaces_have_no_train_validation_overlap(self):
        p=self.pred
        self.assertTrue(p.groupby('patient_id').validation_fold.nunique().eq(1).all())
        self.assertTrue(p.groupby('brats_patient_id').validation_fold.nunique().eq(1).all())
        for f in self.folds:
            tr=p[p.validation_fold.ne(f['fold'])];te=p[p.validation_fold.eq(f['fold'])]
            for key in ['patient_id','brats_patient_id','validation_group']:
                self.assertFalse(set(tr[key])&set(te[key]))
            self.assertEqual(set(te.ID),set(f['test_IDs']))
            self.assertAlmostEqual(f['models']['M1']['parameters']['log_interval_impute_median'],np.nanmedian(tr.log_initial_event_days))

    def test_prediction_does_not_refit_the_imputer(self):
        f=self.folds[0];tr=self.d[self.d.ID.isin(f['train_IDs'])];te=self.d[self.d.ID.isin(f['test_IDs'])].copy()
        m=make_model('M1').fit(tr,tr.tumor_label);before=parameter_record(m,'M1')
        te.loc[:,'log_initial_event_days']=1000000
        m.predict_proba(te)
        self.assertEqual(before,parameter_record(m,'M1'))
        self.assertAlmostEqual(before['log_interval_impute_median'],np.nanmedian(tr.log_initial_event_days))

    def test_future_and_label_columns_cannot_change_predictions(self):
        m=make_model('M1').fit(self.d,self.d.tumor_label)
        altered=self.d.copy();altered['tumor_label']=1-altered.tumor_label
        altered['Overall survival']=999999;altered['MRI_TCT_volume']=9999
        altered['label_source']='altered';altered['validation_fold']=99
        np.testing.assert_array_equal(m.predict_proba(self.d),m.predict_proba(altered))

    def test_paired_bootstrap_zero_difference_for_identical_predictions(self):
        d=self.d.copy();p=.5+d.age_years.to_numpy()/200
        d['M0_oof_probability']=p;d['M1_oof_probability']=p
        intervals,draws=paired_intervals(d,n=30)
        np.testing.assert_array_equal(draws.to_numpy(),0)
        self.assertEqual(intervals['M1_minus_M0']['roc_auc'],dict(lower=0,upper=0))

    def test_oof_probabilities_complete_and_comparator_train_only(self):
        p=self.pred
        self.assertEqual(p.ID.nunique(),len(p))
        for name in ['M0','M1','prior']:self.assertTrue(p[name+'_oof_probability'].between(0,1).all())
        for f in self.folds:
            tr=p[p.validation_fold.ne(f['fold'])];te=p[p.validation_fold.eq(f['fold'])]
            np.testing.assert_allclose(te.prior_oof_probability,tr.tumor_label.mean())


if __name__=='__main__':unittest.main()
