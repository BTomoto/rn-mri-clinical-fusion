"""Create standard nbformat-4 notebooks; execution requires only ordinary Python."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.splitlines(True)}


setup = """from pathlib import Path
import sys, json
import pandas as pd
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'src/rn_public').is_dir())
sys.path.insert(0, str(ROOT / 'src'))
from rn_public.bundle import restore_sources
print('Source restoration:', restore_sources(ROOT))
print('Project root:', ROOT.name)
"""

notebooks = {
"00_data_access_and_provenance.ipynb": [
 md("""# 公开数据获取与来源核验

本研究使用已经公开的去标识资料，不开展新增招募、动物或细胞实验。
这里记录数据来源、许可、校验和与实际下载状态。公开目录存在不等于图像质量合格，也不等于结局可靠。
"""),
 code(setup),
 code("""import hashlib
sources = json.loads((ROOT / 'data/metadata/source_files.json').read_text())
for item in sources:
    p = ROOT / item['local_path']
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    assert actual == item['sha256'], item['filename']
print(pd.DataFrame(sources)[['filename','size_bytes','license','status']].to_string(index=False))
print('All original OpenBTAI table/mask checksums match the acquisition manifest.')
"""),
 code("""archives = pd.read_json(ROOT / 'data/metadata/archive_sources.json')
print(archives[['archive_id','archive_name','archive_size','download_url']].to_string(index=False))
print('To restore small sources/directories: python scripts/download_sources.py')
print('To restore selected MRI: python scripts/download_selected_images.py --workers 6')
"""),
 md("""## 数据范围

OpenBTAI用于主要队列整理。UCSD、Yale和PROTEAS的公开临床文件仅作为可行性核验参考，不自动并入脑坏死预测队列。
源数据与派生数据分开保存。MRI体素保存在 `data/imaging/`，Excel保存数值、索引和审核状态。
"""),
],
"01_cohort_curation_and_audit.ipynb": [
 md("""# 队列整理、时间匹配与终点缺口

首次记录的SRS作为暂定索引治疗。基线窗口为SRS前30天至当天；当天影像尚需核实检查与治疗先后顺序。
多病灶患者不被拆成独立患者。任何后续验证必须按患者分组。
"""),
 code(setup),
 code("""from rn_public.curate import curate
summary = curate(ROOT)
print(pd.Series(summary).to_string())
"""),
 code("""lesions = pd.read_csv(ROOT / 'data/processed/lesions.csv', dtype={'patient_id':str})
assert not lesions.duplicated(['patient_id','lesion_id']).any()
assert (lesions.loc[lesions.rn_time_day.isna(), 'rn_status'] == 'unknown').all()
print('RN source status:')
print(lesions.rn_status.value_counts().to_string())
print('Chronology conflicts:')
print(lesions.loc[lesions.rn_after_first_srs.eq(0), ['lesion_key','first_srs_start_day','rn_time_day']].to_string(index=False))
"""),
 code("""matches = pd.read_csv(ROOT / 'data/processed/baseline_matches.csv', dtype={'patient_id':str})
assert matches.baseline_to_srs_days.between(0,30).all()
print(matches[['lesion_key','baseline_date_code','baseline_to_srs_days','rn_status']].head(10).to_string(index=False))
print('Candidate lesions:', len(matches))
print('Candidate patients:', matches.patient_id.nunique())
print('Candidates with recorded RN timing:', matches.rn_time_day.notna().sum())
print('Final eligible lesions:', matches.final_eligible.sum())
"""),
 md("""## 当前不能据此估计发病率或训练风险模型

128条缺少脑坏死时间的病灶记录保持为未知状态。它们不自动成为阴性对照。
论文的39个脑坏死病灶与表中32条时间记录尚未逐一对齐。
已有形态学和影像组学表可能含结局后影像，不能直接合并进治疗前预测模型。
"""),
],
"02_imaging_download_integrity.ipynb": [
 md("""# 原始影像下载与文件完整性

HTTP Range选择性提取官方ZIP中的原始DICOM，验证每个文件的ZIP CRC32、字节数和SHA256。
这些检查证明文件传输完整；不会替代配准、病灶可见性、伪影、序列身份及分割质量评估。
"""),
 code(setup),
 code("""manifest_path = ROOT / 'data/metadata/downloaded_imaging.jsonl'
if manifest_path.exists():
    manifest = pd.read_json(manifest_path, lines=True, dtype={'patient_id':str,'study_date_code':str})
    print('Downloaded DICOM files:', len(manifest))
    print('Patients:', manifest.patient_id.nunique())
    print('Patient-date pairs:', manifest[['patient_id','study_date_code']].drop_duplicates().shape[0])
    print('Uncompressed bytes:', int(manifest.size_bytes.sum()))
else:
    manifest = pd.DataFrame()
    print('Full selected-image download is not yet complete. Run the documented download script.')
"""),
 code("""import hashlib
if len(manifest):
    failures = []
    for record in manifest.to_dict('records'):
        p = ROOT / record['path']
        if not p.is_file() or p.stat().st_size != record['size_bytes']:
            failures.append(record['path'])
    assert not failures, failures[:5]
    sample = manifest.sample(n=min(20,len(manifest)), random_state=20261028)
    for record in sample.to_dict('records'):
        p = ROOT / record['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == record['sha256']
    print('Every indexed file exists with the expected byte count; 20 deterministic SHA256 spot-checks passed.')
"""),
 code("""series = pd.read_csv(ROOT / 'data/processed/image_series.csv')
print('Name-based sequence hints (not verified imaging labels):')
print(series[['flair_name_hint','t2_name_hint','t1_name_hint']].sum().to_string())
print('Image quality status: pending per-study review and target-lesion segmentation.')
"""),
],
"03_model_readiness_and_analysis_plan.ipynb": [
 md("""# 模型数据准备与分析前检查

主目标：治疗前MRI和临床治疗信息是否提供增量预测信息。
次目标：在同一人群、预测时点及结局窗口下评价早期纵向信息。
死亡需要作为竞争事件处理；不能直接把随访不足或早期死亡归为12个月无事件。
"""),
 code(setup),
 code("""review = pd.read_csv(ROOT / 'data/processed/outcome_review.csv')
print(review.review_status.value_counts().to_string())
required = ['adjudicated_rn_event','reference_standard','evidence_source']
verified = review.review_status.isin(['verified_event','verified_event_free'])
complete = verified & review[required].notna().all(axis=1)
print('Outcome-reviewed lesion rows:', int(complete.sum()))
print('Review fields must be filled from traceable public source evidence; no values are invented.')
"""),
 code("""analysis_plan = pd.DataFrame([
    ['M0','Prespecified clinical and treatment predictors','Penalized competing-risk/survival framework'],
    ['M1','M0 plus baseline MRI features','Same patients, outcome horizon and validation splits as M0'],
    ['M2 (optional)','M1 plus event-preceding early MRI changes','Fixed landmark; compare only within the landmark cohort'],
], columns=['model','inputs','design'])
print(analysis_plan.to_string(index=False))
print('Validation: patient-level resampling; preprocessing and feature selection within training folds.')
print('Evaluation: discrimination, calibration, Brier score and uncertainty; no external validation claim without matching endpoints.')
"""),
 code("""readiness = {
    'outcomes_adjudicated': bool(complete.sum() > 0),
    'target_lesion_segmentation_qc_complete': False,
    'prediction_horizon_and_censoring_confirmed': False,
}
print(pd.Series(readiness).to_string())
if not all(readiness.values()):
    print('MODEL FITTING NOT STARTED: the current release is a data acquisition and curation project.')
"""),
],
}
for name, cells in notebooks.items():
    for i, cell in enumerate(cells):
        cell['id'] = f"cell-{i:03d}"
    book = dict(cells=cells, metadata=dict(kernelspec=dict(display_name="Python 3", language="python", name="python3"), language_info=dict(name="python", version="3.12")), nbformat=4, nbformat_minor=5)
    (ROOT / 'notebooks' / name).write_text(json.dumps(book, ensure_ascii=False, indent=1))
print('Created', len(notebooks), 'notebooks')
