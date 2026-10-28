from pathlib import Path
import sys
import unittest
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.endpoint_followup import read_clinical,followup_availability


class EndpointFollowupTests(unittest.TestCase):
    def test_current_source_bytes_match_provenance(self):
        meta=ROOT/'data/metadata/endpoint_followup'
        for source in json.loads((meta/'molab_downloaded_sources.json').read_text()):
            self.assertEqual(hashlib.sha256((ROOT/source['local_path']).read_bytes()).hexdigest(),source['sha256'])
        inv=json.loads((meta/'molab_excel_archive_inventory.json').read_text())
        item=next(x for x in inv['files'] if x['name']=='OpenBTAI_METS_ClinicalData_Sept2023.xlsx')
        path=ROOT/'data/raw/openbtai_molab_current'/item['name']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),item['sha256'])

    def test_wrong_source_layout_is_rejected(self):
        with self.assertRaises(ValueError):
            read_clinical(ROOT/'data/raw/openbtai/OpenBTAI_METS_ClinicalData.xlsx','molab')

    def test_author_version_recovers_new_and_revised_rn_times(self):
        d=pd.read_csv(ROOT/'data/processed/clinical_current.csv').set_index('lesion_key')
        self.assertEqual(d.loc['40001_L1','rn_time_day'],545)
        self.assertEqual(d.loc['40024_L1','rn_time_day'],336)
        self.assertEqual(d.loc['40102_L2','rn_time_day'],749)
        self.assertEqual(d.loc['20001_L1','first_srs_start_day'],239)
        self.assertEqual(d.rn_time_day.notna().sum(),35)
        self.assertTrue(d.loc[d.rn_time_day.isna(),'rn_status'].eq('unknown').all())

    def test_a_late_mri_is_not_a_negative_outcome(self):
        current=pd.DataFrame([dict(lesion_key='1_L1',patient_id='1',lesion_id=1,
            first_srs_start_day=100,rn_time_day=float('nan'),death_day=600,rn_status='unknown')])
        scans=pd.DataFrame([dict(lesion_key='1_L1',study_day=465)])
        studies=pd.DataFrame([dict(patient_id='1',study_day=90),dict(patient_id='1',study_day=465)])
        masks=pd.DataFrame(columns=['lesion_key','study_date_code','study_day'])
        availability,horizons=followup_availability(current,scans,studies,masks)
        h=horizons[horizons.horizon_days==365].iloc[0]
        self.assertEqual(h.source_scan_on_or_after_horizon_before_death,1)
        self.assertEqual(h.verified_non_event,0)
        self.assertTrue(pd.isna(h.verified_event_free_followup_day))
        self.assertEqual(availability.iloc[0].rn_timing_class,'unknown')

    def test_current_baseline_join_is_unique_and_precedes_srs(self):
        f=pd.read_csv(ROOT/'data/processed/baseline_features_current.csv')
        self.assertEqual(len(f),f.lesion_key.nunique())
        self.assertEqual(len(f),54)
        self.assertIn('40093_L3',set(f.lesion_key))
        self.assertTrue((f.baseline_mask_day < f.first_srs_start_day).all())
        self.assertEqual(f.rn_time_day.notna().sum(),18)
        self.assertEqual(f.use_for_model.sum(),0)


if __name__=='__main__':unittest.main()
