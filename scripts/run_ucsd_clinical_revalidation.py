from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_clinical_revalidation import run
if __name__=='__main__':print(json.dumps(run(ROOT),indent=2))
