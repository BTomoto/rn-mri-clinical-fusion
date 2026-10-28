"""Guard against patient leakage, unverified source substitution and forbidden inputs."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_clinical_baseline import make_cohort, grouped_predictions, make_model, FEATURES


class UCSDBaselineTests(unittest.TestCase):
    def test_source_cohort_labels_and_original_history(self):
        d=make_cohort(ROOT)
        self.assertEqual((len(d),d.patient_id.nunique(),d.tumor_label.sum()),(243,178,192))
        self.assertTrue(d.loc[d.tumor_label.eq(0),'source_row_negative_list'].notna().all())
        self.assertTrue(d.loc[d.tumor_label.eq(1),'source_row_negative_list'].isna().all())
        old=pd.read_csv(ROOT/'data/processed/ucsd_ptgbm_label_feasibility.csv')
        self.assertEqual(old.use_for_model.sum(),0)
        self.assertEqual(d.diagnosis_text_anomaly.sum(),1)

    def test_fingerprint_rejects_substituted_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data/raw/reference';path.mkdir(parents=True)
            (path/'ucsd_ptgbm_clinical_v3.xlsx').write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError,'fingerprint'):
                make_cohort(Path(tmp))

    def test_oof_patient_isolation_with_cross_class_patients(self):
        d=make_cohort(ROOT)
        oof,folds=grouped_predictions(d)
        self.assertEqual(oof.ID.nunique(),243)
        self.assertTrue(oof.groupby('patient_id').validation_fold.nunique().eq(1).all())
        self.assertTrue(oof.oof_tumor_probability.between(0,1).all())
        for f in folds:
            tr=oof[oof.validation_fold.ne(f['fold'])]
            te=oof[oof.validation_fold.eq(f['fold'])]
            self.assertFalse(set(tr.patient_id)&set(te.patient_id))
            self.assertAlmostEqual(f['train_age_mean'],tr.age_years.mean())
            self.assertAlmostEqual(f['train_age_sd'],tr.age_years.std(ddof=0))
            np.testing.assert_allclose(te.oof_prevalence_only_probability,tr.tumor_label.mean())

    def test_future_and_label_fields_cannot_change_predictions(self):
        d=make_cohort(ROOT)
        model=make_model().fit(d,d.tumor_label)
        changed=d.copy()
        changed['tumor_label']=1-d.tumor_label
        changed['negative_list_dx']='altered_label'
        changed['Overall survival']=1000000
        changed['primary_diagnosis_raw']='altered_diagnosis'
        np.testing.assert_array_equal(model.predict_proba(d),model.predict_proba(changed))
        self.assertEqual(FEATURES,['age_years','sex_male'])


if __name__=='__main__':unittest.main()
