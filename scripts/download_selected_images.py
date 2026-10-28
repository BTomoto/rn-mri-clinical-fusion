"""Download all DICOM series for selected baseline/early patient-date pairs.

Selection is based on temporal matching only. It does not assert lesion visibility,
correct sequence classification, valid outcomes, or final study eligibility.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rn_public.remotezip import download_members

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--workers", type=int, default=6)
parser.add_argument("--patient", help="Optional public pseudonymous patient ID for a pilot download")
args = parser.parse_args()
archives = json.loads((root / "data/metadata/archive_sources.json").read_text())
groups = defaultdict(list)
for line in (root / "data/metadata/selected_dicom_members.jsonl").open():
    record = json.loads(line)
    if args.patient is None or record["patient_id"] == args.patient:
        groups[record["archive_id"]].append(record)
summary = []
for archive in archives:
    entries = groups[archive["archive_id"]]
    if not entries:
        continue
    print(f"{archive['archive_id']}: verifying/downloading {len(entries)} members", flush=True)
    result = download_members(archive["download_url"], entries, root / "data/imaging/dicom", args.workers)
    result["archive_id"] = archive["archive_id"]
    summary.append(result)
    (root / "reports/image_download_progress.json").write_text(json.dumps(summary, indent=2))
    print(result, flush=True)

manifest = []
for archive_id, entries in groups.items():
    for e in entries:
        p = root / "data/imaging/dicom" / e["name"]
        if not p.is_file():
            raise RuntimeError(f"Missing downloaded member: {e['name']}")
        manifest.append(dict(path=str(p.relative_to(root)), size_bytes=p.stat().st_size,
                             sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                             archive_id=archive_id, zip_crc32=e["crc32"],
                             patient_id=e["patient_id"], study_date_code=e["study_date_code"]))
suffix = "_" + args.patient if args.patient else ""
with (root / f"data/metadata/downloaded_imaging{suffix}.jsonl").open("w") as f:
    for r in manifest:
        f.write(json.dumps(r) + "\n")
print(f"Verified {len(manifest)} DICOM files", flush=True)
