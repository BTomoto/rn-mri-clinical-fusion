"""Run only the approved UCSD clinical baseline, without MRI or original-risk fitting."""
from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_clinical_baseline import run
if __name__ == '__main__':
    s = run(ROOT)
    print(json.dumps({k: s[k] for k in ['timepoints', 'patients', 'logistic_oof', 'prevalence_only_oof']}, indent=2))
