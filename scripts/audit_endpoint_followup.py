from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from rn_public.endpoint_followup import run
print(json.dumps(run(root),indent=2))
