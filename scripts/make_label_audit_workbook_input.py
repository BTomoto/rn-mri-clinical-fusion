"""Prepare an Excel review of public-label feasibility; no analysis eligibility."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
a=pd.read_csv(ROOT/'data/processed/ucsd_ptgbm_label_feasibility.csv')
counts=pd.read_csv(ROOT/'data/processed/ucsd_ptgbm_subtype_count_comparison.csv')
summary=json.loads((ROOT/'reports/public_label_feasibility_20261029.json').read_text())
sources=[['TCIA当前数据页','https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/','243=192肿瘤+51治疗相关改变；亚型介绍与文件有差异'],
 ['临床v3文件','https://www.cancerimagingarchive.net/wp-content/uploads/UCSD_PTGBM-clinical-information_v3_2026-12-Mar.xlsx','243时间点、178患者；本轮已下载并校验SHA256'],
 ['51条分类明细','https://www.cancerimagingarchive.net/wp-content/uploads/details_of_negative_cases_TCIA.xlsx','全部ID可连接到v3临床表；RN记录实际7条'],
 ['RN-D3附录','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13490108/supplementaryFiles?includeInlineImage=false','已核查3表2图；未发现可连接病灶标签表']]
(ROOT/'reports/label_audit_workbook_input.json').write_text(json.dumps(dict(headers=a.columns.tolist(),rows=a.astype(object).where(a.notna(),None).values.tolist(),counts=counts.to_dict('records'),summary=summary,sources=sources),ensure_ascii=False,allow_nan=False))
print('Prepared label-feasibility workbook input')
