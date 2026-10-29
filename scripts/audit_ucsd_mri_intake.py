"""Audit two downloaded UCSD samples. Does not download, extract archives or fit models."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_mri_intake import run

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-root', type=Path, help='Root containing the actual original-named NIfTI files')
    p.add_argument('--output-root', type=Path, help='Separate QC result directory; default reports/ucsd_mri_intake')
    args = p.parse_args()
    result = run(ROOT, args.input_root, args.output_root)
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    # Successful script completion does not mean actual files or scientific acceptance exist.
    sys.exit(0 if result['summary']['minimal_FLAIR_batch_technical_pass'] else 2)
