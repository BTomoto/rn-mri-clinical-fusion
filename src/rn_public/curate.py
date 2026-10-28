"""Normalize published tables and construct explicitly provisional image matches.

Source blanks in radiation-necrosis timing are UNKNOWN, never event-free labels.
No prediction models are fit by this module.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
import pandas as pd
from .remotezip import parse_directory

ORIGIN = dt.datetime(1900, 1, 1)


def numeric(x):
    return isinstance(x, (float, int)) and not isinstance(x, bool) and pd.notna(x)


def clean(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, str):
        return x.strip() or None
    if isinstance(x, (dt.datetime, dt.date)):
        return x.isoformat()
    return x.item() if hasattr(x, "item") else x


def write_records(root, name, records):
    df = pd.DataFrame(records)
    df.to_csv(root / "data/processed" / f"{name}.csv", index=False, encoding="utf-8")
    return df


def curate(root: Path):
    root = root.resolve()
    from .bundle import restore_sources
    restore_sources(root)
    raw = root / "data/raw/openbtai"
    out = root / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    # read_excel is used only for extraction. Excel authoring is separate.
    clinical = pd.read_excel(raw / "OpenBTAI_METS_ClinicalData.xlsx", header=None)
    lesions, treatments, patient_records, clinical_raw = [], [], {}, []
    issues = []
    for index, row in clinical.iterrows():
        r = list(row) + [None] * 200
        if index < 15 or not numeric(r[0]) or not numeric(r[4]):
            continue
        pid, lid = str(int(r[0])), int(r[4])
        key = f"{pid}_L{lid}"
        rn = clean(r[32]) if numeric(r[32]) else None
        srs = clean(r[22]) if numeric(r[22]) else None
        death = clean(r[54]) if numeric(r[54]) else None
        record = dict(patient_id=pid, lesion_id=lid, lesion_key=key,
                      age_at_first_mri_years=clean(r[1]), sex_code=clean(r[2]),
                      gpa_raw=clean(r[3]), primary_tumor_code=clean(r[5]),
                      primary_subtype_code=clean(r[6]), egfr_raw=clean(r[7]),
                      alk_raw=clean(r[8]), ros1_raw=clean(r[9]),
                      tn_stage_raw=clean(r[10]), tumor_stage_raw=clean(r[11]),
                      rn_time_day=rn, rn_status="recorded_event_time" if rn is not None else "unknown",
                      rn_reference_standard="not_provided_per_lesion",
                      first_srs_start_day=srs, first_srs_end_day=clean(r[23]),
                      first_srs_dose_per_fraction_gy=clean(r[20]),
                      first_srs_fractions=clean(r[21]), death_day=death,
                      death_recorded=clean(r[53]), surgery_type_raw=clean(r[33]),
                      surgery_day_raw=clean(r[34]),
                      rn_after_first_srs=(int(rn > srs) if rn is not None and srs is not None else None),
                      outcome_adjudicated=0, image_qc_complete=0,
                      final_eligible=0, eligibility_status="pending_outcome_and_image_review",
                      source_row_excel=index+1)
        lesions.append(record)
        patient_records.setdefault(pid, {k: record[k] for k in ["patient_id", "age_at_first_mri_years", "sex_code", "primary_tumor_code", "death_day", "death_recorded"]})
        clinical_raw.append(dict(source_row_excel=index+1, **{f"col_{i+1:03d}": clean(v) for i, v in enumerate(list(row)[:79])}))
        for typ, ix, number in [("WBRT", 12, 1), ("WBRT", 16, 2), ("SRS", 20, 1), ("SRS", 24, 2), ("SRS", 28, 3)]:
            if any(clean(v) is not None for v in r[ix:ix+4]):
                treatments.append(dict(patient_id=pid, lesion_id=lid, lesion_key=key,
                                       treatment_type=typ, treatment_number=number,
                                       dose_per_fraction_gy=clean(r[ix]), fractions=clean(r[ix+1]),
                                       start_day=clean(r[ix+2]), end_day=clean(r[ix+3])))
        if rn is None:
            issues.append(dict(lesion_key=key, issue="unknown_rn_status", detail="Blank RN time is not a confirmed non-event; establish surveillance/censoring first."))
        elif srs is not None and rn <= srs:
            issues.append(dict(lesion_key=key, issue="rn_not_after_recorded_first_srs", detail=f"rn_day={rn}; srs_day={srs}; verify prior treatment and source entry; no correction applied."))
    df_lesions = write_records(root, "lesions", lesions)
    write_records(root, "patients", list(patient_records.values()))
    write_records(root, "treatments", treatments)
    write_records(root, "clinical_source_rows", clinical_raw)

    archive_meta = json.loads((root / "data/metadata/archive_sources.json").read_text())
    all_entries, series = [], {}
    for archive in archive_meta:
        for e in parse_directory((root / archive["directory_path"]).read_bytes()):
            ss = e["name"].split("/")
            if len(ss) < 4 or not ss[0].isdigit() or not re.fullmatch(r"\d{8}", ss[1]) or not e["name"].lower().endswith(".dcm"):
                continue
            pid, date, label = str(int(ss[0])), ss[1], ss[2]
            day = (dt.datetime.strptime(date, "%Y%m%d") - ORIGIN).days
            e.update(archive_id=archive["archive_id"], patient_id=pid, study_date_code=date,
                     study_day=day, series_name=label)
            all_entries.append(e)
            key = (pid, date, label, archive["archive_id"])
            if key not in series:
                upper = label.upper()
                series[key] = dict(patient_id=pid, study_date_code=date, study_day=day,
                                   series_name=label, archive_id=archive["archive_id"],
                                   flair_name_hint=int("FLAIR" in upper), t2_name_hint=int("T2" in upper),
                                   t1_name_hint=int("T1" in upper or "BRAVO" in upper or "FSPGR" in upper),
                                   sequence_verified=0, dicom_files=0, compressed_bytes=0)
            series[key]["dicom_files"] += 1
            series[key]["compressed_bytes"] += e["compressed_size"]
    write_records(root, "image_series", list(series.values()))
    studies = {}
    for rec in series.values():
        key = (rec["patient_id"], rec["study_date_code"])
        if key not in studies:
            studies[key] = {k: rec[k] for k in ["patient_id", "study_date_code", "study_day"]}
            studies[key].update(series_count=0, flair_name_hint=0, t2_name_hint=0,
                                t1_name_hint=0, compressed_bytes=0, image_qc_complete=0)
        a = studies[key]
        a["series_count"] += 1
        for k in ["flair_name_hint", "t2_name_hint", "t1_name_hint"]:
            a[k] = max(a[k], rec[k])
        a["compressed_bytes"] += rec["compressed_bytes"]
    write_records(root, "image_studies", list(studies.values()))
    # Earliest recorded SRS on each lesion row is a provisional index treatment.
    by_patient = defaultdict(list)
    for v in studies.values():
        by_patient[v["patient_id"]].append(v)
    selected = set()
    matches = []
    for lesion in lesions:
        srs = lesion["first_srs_start_day"]
        if srs is None:
            continue
        rn = lesion["rn_time_day"]
        if rn is not None and rn <= srs:
            continue
        base = [v for v in by_patient[lesion["patient_id"]] if -30 <= v["study_day"]-srs <= 0]
        if not base:
            continue
        b = max(base, key=lambda v: v["study_day"])
        early = [v for v in by_patient[lesion["patient_id"]] if 30 <= v["study_day"]-srs <= 90]
        e = min(early, key=lambda v: abs(v["study_day"]-srs-90)) if early else None
        selected.add((b["patient_id"], b["study_date_code"]))
        if e:
            selected.add((e["patient_id"], e["study_date_code"]))
        matches.append(dict(lesion_key=lesion["lesion_key"], patient_id=lesion["patient_id"],
                            lesion_id=lesion["lesion_id"], first_srs_start_day=srs,
                            baseline_date_code=b["study_date_code"], baseline_day=b["study_day"],
                            baseline_to_srs_days=srs-b["study_day"],
                            baseline_flair_name_hint=b["flair_name_hint"],
                            baseline_same_day_as_srs=int(b["study_day"] == srs),
                            early_date_code=e["study_date_code"] if e else None,
                            early_day=e["study_day"] if e else None,
                            early_flair_name_hint=e["flair_name_hint"] if e else None,
                            rn_time_day=rn, rn_status=lesion["rn_status"],
                            death_day=lesion["death_day"],
                            dynamic_day90_time_candidate=int(bool(e) and (rn is None or rn>srs+90) and lesion["death_day"]>srs+90),
                            target_lesion_visible=None, image_qc_complete=0, outcome_adjudicated=0,
                            final_eligible=0, status="directory_match_only"))
    write_records(root, "baseline_matches", matches)
    selected_entries = [e for e in all_entries if (e["patient_id"], e["study_date_code"]) in selected]
    with (root / "data/metadata/selected_dicom_members.jsonl").open("w") as f:
        for e in selected_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    write_records(root, "quality_issues", issues)

    morph = pd.read_excel(raw / "OpenBTAI_MORPHOLOGICAL_MEASUREMENTS.xlsx")
    morph = morph[morph["PATIENT"].notna()].iloc[:, :17].copy()
    morph = morph.rename(columns={"PATIENT": "patient_id", "LESION": "lesion_id", "TIME POINT": "study_date_code"})
    morph["patient_id"] = morph["patient_id"].astype(int).astype(str)
    morph["lesion_id"] = morph["lesion_id"].astype(int)
    morph["study_date_code"] = morph["study_date_code"].astype(int).astype(str)
    morph["lesion_key"] = morph["patient_id"] + "_L" + morph["lesion_id"].astype(str)
    morph["study_day"] = morph["study_date_code"].apply(lambda t: (dt.datetime.strptime(t, "%Y%m%d")-ORIGIN).days)
    morph["source_volume_unit"] = "cm3_confirm_against_image_geometry"
    morph.to_csv(out / "morphology_existing.csv", index=False)
    # Preserve all original radiomics, but keep the Excel working view narrow.
    radio = pd.read_excel(raw / "OpenBTAI_Radiomic.xlsx")
    selected_features = [c for c in radio if c.startswith("original_shape_") or c in [
        "Patient", "Timepoint", "Lesion", "Segment", "Image", "Mask",
        "original_firstorder_Mean", "original_firstorder_Entropy", "original_firstorder_Skewness",
        "original_firstorder_Kurtosis", "original_firstorder_10Percentile", "original_firstorder_90Percentile"]]
    radio = radio[radio["Segment"] == "Total"][selected_features].copy()
    radio["Patient"] = radio["Patient"].astype(int).astype(str)
    radio["Timepoint"] = radio["Timepoint"].astype(int).astype(str)
    radio["feature_qc_complete"] = 0
    radio["use_for_model"] = 0
    radio.to_csv(out / "radiomics_existing_total.csv", index=False)

    counts = dict(patients=len(patient_records), clinical_lesion_rows=len(lesions),
                  rn_time_records=sum(r["rn_time_day"] is not None for r in lesions),
                  rn_time_patients=len({r["patient_id"] for r in lesions if r["rn_time_day"] is not None}),
                  unknown_rn_rows=sum(r["rn_time_day"] is None for r in lesions),
                  image_patient_dates=len(studies), image_series=len(series),
                  baseline_directory_candidates=len(matches),
                  baseline_candidate_patients=len({r["patient_id"] for r in matches}),
                  baseline_candidate_rn_times=sum(r["rn_time_day"] is not None for r in matches),
                  selected_patient_dates=len(selected), selected_dicom_files=len(selected_entries),
                  selected_compressed_bytes=sum(r["compressed_size"] for r in selected_entries),
                  final_eligible_lesions=0, modeling_status="blocked_pending_outcome_and_image_review")
    (root / "reports/curation_summary.json").write_text(json.dumps(counts, indent=2))
    return counts
