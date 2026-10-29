"""Fetch the fixed six-case sample and run technical ROI/normalisation diagnostics."""
from pathlib import Path
import sys,json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_roi_pilot import run
if __name__ == '__main__':
    print(json.dumps(run(ROOT), indent=2))
