"""Acquire the fixed available cohort and extract eight prespecified image features."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_batch_features import run,prepare,download_all
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-root',type=Path);p.add_argument('--download-only',action='store_true');p.add_argument('--skip-download',action='store_true');p.add_argument('--workers',type=int,default=4)
 a=p.parse_args();batch=a.input_root or ROOT.parent/'ucsd_batch_sources'
 if a.download_only:
  _,_,m=prepare(ROOT);r=download_all(ROOT,batch,m);print(json.dumps(dict(requested=len(m),available=sum(x['success'] for x in r)),indent=2))
 else:print(json.dumps(run(ROOT,batch,download=not a.skip_download,workers=a.workers),indent=2))
