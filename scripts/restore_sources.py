"""Run once after cloning, or let each notebook restore sources automatically."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from rn_public.bundle import restore_sources
print(restore_sources(root))
