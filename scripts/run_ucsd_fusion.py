"""Run the fixed Stage18 analysis or freeze its folds without fitting."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_fusion import freeze_plan,run
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze-only',action='store_true');a=p.parse_args()
 if a.freeze_only:
  d,e,m,lock=freeze_plan(ROOT);print(m.groupby('validation_fold').agg(scans=('ID','size'),tumor=('tumor_label','sum')))
  print(json.dumps(lock,indent=2))
 else:
  s=run(ROOT);print(json.dumps({k:s[k] for k in ['scans','source_patients','metrics','bootstrap_valid']},indent=2))
