"""Download fixed 0002/0005 technical samples through public HTTPS, then decode/QC."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_mri_mirror import run

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--refresh-inventory', action='store_true', help='Refresh five known public release inventories')
    args = p.parse_args()
    print(json.dumps(run(ROOT, refresh=args.refresh_inventory), indent=2))
