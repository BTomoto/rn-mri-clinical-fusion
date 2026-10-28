"""Refresh public clinical-file fingerprint and assess the original model gate."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DATE='2026-10-29'
URL='https://dw.molab.es/indices/bm1/OpenBTAI_METS_ClinicalData_Nov2023.xlsx'


def run(refresh=False):
    meta=ROOT/'data/metadata/endpoint_gate_20261029';meta.mkdir(exist_ok=True)
    receipt=meta/'clinical_source_recheck.json'
    current=ROOT/'data/raw/openbtai_molab_current/OpenBTAI_METS_ClinicalData_Nov2023.xlsx'
    expected=hashlib.sha256(current.read_bytes()).hexdigest()
    if refresh:
        with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'RNPublicDataAudit/1.0'}),timeout=60) as r:
            b=r.read();resolved=r.url
        digest=hashlib.sha256(b).hexdigest()
        record=dict(checked_date=DATE,url=URL,resolved_url=resolved,size_bytes=len(b),sha256=digest,
            prior_sha256=expected,unchanged=digest==expected)
        if digest!=expected:
            new=ROOT/'data/raw/openbtai_molab_recheck_20261029';new.mkdir(exist_ok=True)
            (new/'OpenBTAI_METS_ClinicalData_Nov2023.xlsx').write_bytes(b)
        receipt.write_text(json.dumps(record,indent=2))
    record=json.loads(receipt.read_text())
    if record['prior_sha256']!=expected:raise ValueError('Clinical audit input fingerprint changed')
    c=pd.read_csv(ROOT/'data/processed/clinical_current.csv')
    a=pd.read_csv(ROOT/'data/processed/followup_availability_current.csv')
    features=pd.read_csv(ROOT/'data/processed/baseline_features_current.csv')
    verified_non_events=int(c.verified_non_event.sum())
    verified_event_free=int(a.verified_event_free_followup_day.notna().sum())
    enabled_keys=set(features.loc[features.use_for_model==1,'lesion_key'])
    eligible=a[a.lesion_key.isin(enabled_keys)]
    # A fully documented subset could be analyzed; all 160 raw rows need not be complete.
    ready=bool(record['unchanged'] and len(eligible)>0 and eligible.outcome_adjudicated.eq(1).all()
        and eligible.rn_time_day.notna().any() and eligible.verified_non_event.gt(0).any()
        and eligible.verified_event_free_followup_day.notna().any())
    summary=dict(checked_date=DATE,current_clinical_source_unchanged=record['unchanged'],clinical_lesions=len(c),
        recorded_rn_times=int(c.rn_time_day.notna().sum()),unknown_rn=int(c.rn_time_day.isna().sum()),
        verified_non_events=verified_non_events,verified_event_free_followup_records=verified_event_free,
        baseline_mask_candidates=len(features),baseline_candidates_enabled_for_model=int(features.use_for_model.sum()),
        original_risk_prediction_model_ready=ready,prediction_model_fitted=False,
        decision='do_not_train_original_risk_model_with_current_verified_public_endpoints',
        scope_limit='Current verified source set; not proof that no additional public labels exist anywhere',
        blockers=['Blank RN does not establish an event-free outcome or censoring date',
                  'Published diagnostic specificity cohorts do not provide verified pretreatment event-free follow-up for this cohort',
                  'Public lesion-level reference-standard mapping remains incomplete'],
        next_action='Prioritize public endpoint provenance or a fully labeled public cohort before expanding cohort-wide image processing',
        clinical_source_sha256=expected)
    (ROOT/'reports/modeling_gate_20261029.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True);return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--refresh',action='store_true')
    run(parser.parse_args().refresh)
