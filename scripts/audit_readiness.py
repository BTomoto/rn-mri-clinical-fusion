from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from rn_public.readiness import run_audit
print(json.dumps(run_audit(root),indent=2))
