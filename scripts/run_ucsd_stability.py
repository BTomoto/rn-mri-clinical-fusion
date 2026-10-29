"""Run Stage19 fixed stability analysis, or freeze its complete plans."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_stability import freeze_plan,run
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze-only',action='store_true');a=p.parse_args()
 if a.freeze_only:
  d,s,m,p,sm,sp,lock=freeze_plan(ROOT)
  print('Fixed repeats:',len(p),'repeated manifest rows:',len(m),'single scans:',len(s))
  print('Invalid frozen folds:',sum(not f['valid'] for plan in p for f in plan['folds'])+sum(not f['valid'] for f in sp))
  print(s.tumor_label.value_counts().to_dict())
 else:
  s=run(ROOT);print('Complete repeats:',s['repeats_complete'],'single complete:',s['single_scan']['complete'])
