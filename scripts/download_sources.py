"""Restore public source files and archive directories from documented URLs."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rn_public.remotezip import fetch_directory
from rn_public.bundle import restore_sources

root = Path(__file__).resolve().parents[1]
restore_sources(root)
for item in json.loads((root / "data/metadata/source_files.json").read_text()):
    p = root / item["local_path"]
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]:
        print("Verified existing", p.name)
        continue
    p.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(item["download_url"], timeout=55) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise ValueError(f"Source changed or transfer corrupt: {p.name}")
    p.write_bytes(data)
for a in json.loads((root / "data/metadata/archive_sources.json").read_text()):
    p = root / a["directory_path"]
    if not p.exists():
        p.write_bytes(fetch_directory(a["download_url"], a["archive_size"]))
print("All curation inputs available")
