"""Create a focused reproducible audit notebook; execute with nbclient."""
from pathlib import Path
import nbformat as nbf
import sys

root=Path(__file__).resolve().parents[1]
nb=nbf.v4.new_notebook()
md=nbf.v4.new_markdown_cell
code=nbf.v4.new_code_cell
nb.cells=[
md('# 04 结局、时间与分割可用性核查\n\n核查日期：2026-10-28。仅使用公开数据。此Notebook不拟合预测模型。\n\n临床表中的空白坏死时间保持未知，后续MRI日期不等于该病灶无事件随访。掩膜非增强/坏死成分也不等于放射性坏死诊断。'),
code("from pathlib import Path\nimport sys, json\nimport pandas as pd\nROOT = Path.cwd()\nif ROOT.name == 'notebooks': ROOT = ROOT.parent\nassert (ROOT/'src/rn_public').exists()\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.bundle import restore_sources\nfrom rn_public.readiness import audit_outcomes\nrestore_sources(ROOT)\noutcomes, counts = audit_outcomes(ROOT)\nprint(json.dumps(counts, indent=2))"),
md('## 结局时间异常\n\n所列记录需要澄清原始字段和治疗史。不能凭经验把异常时间改成合理数值。已记录事件时间也不表示逐例诊断依据已核实。'),
code("flags = outcomes[(outcomes.rn_after_death == 1) | (outcomes.index_srs_after_death == 1) | (outcomes.rn_evidence_class == 'rn_at_or_before_index_srs')]\nprint(flags[['lesion_key','first_srs_start_day','rn_time_day','death_day','rn_evidence_class']].to_string(index=False))\nassert outcomes.loc[outcomes.rn_time_day.isna(),'rn_evidence_class'].eq('unknown').all()\nassert outcomes.verified_non_event.sum() == 0\nassert outcomes.final_eligible.sum() == 0"),
md('## 已有分割覆盖\n\n全部NIfTI掩膜可用 `python scripts/audit_readiness.py` 重新检查。以下读取该脚本产生的逐文件和逐病灶结果。标签编号的病灶/成分解释通过体积核对获得，尚需原始编码说明确认；它们没有提供RN对照标签。'),
code("masks = pd.read_csv(ROOT/'data/processed/mask_file_audit.csv')\nmask_lesions = pd.read_csv(ROOT/'data/processed/mask_lesion_audit.csv')\nsummary = json.loads((ROOT/'reports/readiness_audit.json').read_text())\nprint(json.dumps(summary['masks'],indent=2))\nprint('Baseline actual mask coverage:', int(outcomes.baseline_actual_mask_available.sum()))\nprint('Recorded RN times among those:', int(((outcomes.baseline_actual_mask_available == 1) & outcomes.rn_time_day.notna()).sum()))\nprint('Morphology dates alone undercount baseline coverage because of mixed date coding.')\nassert len(masks) == summary['masks']['mask_files']\nassert len(mask_lesions) == summary['masks']['mask_lesion_time_records']"),
md('## DICOM抽样检查范围\n\n每个选定目录按ZIP排列抽取首尾文件。检查CRC、可读性和基本头信息。这里的首尾不是按空间位置排序的首尾切片。未检查所有切片的空间完整性、像素、运动伪影、T1增强/FLAIR配准或目标病灶定位，因此不能标记为完整影像质控。'),
code("dicom = pd.read_csv(ROOT/'data/processed/dicom_sample_audit.csv')\nprint('Directories:',len(dicom),'sampled files:',int(dicom.sampled_files.sum()))\nprint(dicom.sample_read_status.value_counts().to_string())\nprint('Sample series UID consistent:',int(dicom.sample_same_series_uid.sum()))\nprint('Sample geometry consistent:',int(dicom.sample_same_geometry.sum()))\nprint('Full-series QC completed:',int(dicom.full_series_qc_complete.sum()))\nassert dicom.full_series_qc_complete.sum() == 0"),
md('## 公开证据与当前结论\n\n原始论文报告39个RN病灶，当前临床文件只有32个数值时间。没有找到可公开下载且能对应到本文件的补足标签表。后续鉴别研究不能替代治疗前风险研究的事件/非事件随访。完整结局和基线分割解决前，不输出AUC、风险率或临床效能。'),
code("evidence = json.loads((ROOT/'data/metadata/endpoint_evidence/reviewed_sources.json').read_text())\nfor source in evidence:\n    print(source['source_id'],source['url'])\n    print(source['endpoint_action'])\nprint('Modeling status:',summary['modeling_status'])")
]
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
             'language_info':{'name':'python','version':sys.version.split()[0]},
             'audit_scope':'public endpoints, timeline and structural image availability; no model training'}
nbf.write(nb,root/'notebooks/04_readiness_audit.ipynb')
print('Created notebooks/04_readiness_audit.ipynb')
