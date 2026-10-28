from pathlib import Path
import json
import sys
import nbformat as nbf

root=Path(__file__).resolve().parents[1]
md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
nb=nbf.v4.new_notebook(cells=[
 md('# 05 原作者临床版本与随访可用性\n\n原作者网站的临床下载按钮提供Nov2023文件，整套Excel包中提供Sept2023文件；两份原始文件保留。此Notebook使用Nov2023作临床来源，影像组学特征明确保留Figshare版本标识。\n\n这里统计的是记录和资料可用性，不是RN发生风险，也不将空白RN或存在后续MRI自动编码为阴性。'),
 code("from pathlib import Path\nimport sys,json,hashlib\nimport pandas as pd\nROOT=Path.cwd()\nif ROOT.name=='notebooks':ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.endpoint_followup import run\nsources=json.loads((ROOT/'data/metadata/endpoint_followup/molab_downloaded_sources.json').read_text())\nfor source in sources:\n    p=ROOT/source['local_path']\n    assert hashlib.sha256(p.read_bytes()).hexdigest()==source['sha256']\ninventory=json.loads((ROOT/'data/metadata/endpoint_followup/molab_excel_archive_inventory.json').read_text())\nsept=next(x for x in inventory['files'] if x['name']=='OpenBTAI_METS_ClinicalData_Sept2023.xlsx')\nassert hashlib.sha256((ROOT/'data/raw/openbtai_molab_current'/sept['name']).read_bytes()).hexdigest()==sept['sha256']\nsummary=run(ROOT)\nprint(json.dumps(summary,indent=2))"),
 md('## 结局及治疗时间更新\n\n对照旧Figshare文件，新版新增3条坏死时间，修改3条已有坏死时间，并补充8条首次SRS起始时间。新旧版本不混写。数据中的n/a、空格、编码和格式变化另行保留，不把所有文本差异解释成临床事实的改变。'),
 code("changes=pd.read_csv(ROOT/'data/processed/clinical_version_changes.csv')\nimportant=changes[changes.field.isin(['rn_time_day','first_srs_start_day'])]\nprint(important[['lesion_key','field','figshare_value','molab_current_value','current_source_row']].to_string(index=False))\nprint('Shared-field differences between September and November:',summary['sept_nov_shared_field_differences'])"),
 md('## 更新后的基线特征候选\n\n以首次记录SRS为暂定索引，MRI严格早于治疗且在其前30天内。病例必须进一步核实完整治疗史、病灶定位、影像质量与诊断依据。'),
 code("f=pd.read_csv(ROOT/'data/processed/baseline_features_current.csv')\nprint('Lesions',len(f),'patients',f.patient_id.nunique(),'recorded RN times',f.rn_time_day.notna().sum())\nassert len(f)==f.lesion_key.nunique()\nassert f.use_for_model.sum()==0\nprint(f[['lesion_key','baseline_mask_date_code','first_srs_start_day','rn_time_day','rn_status']].head(8).to_string(index=False))"),
 md('## 180日与365日资料覆盖\n\n这些是资料可用性核查窗口，不是已选定的预测期限。存在期限后的MRI只能证明有检查资料，不能证明此前未发生坏死。死亡数、MRI数及记录事件数之间可以重叠，不能相加构成竞争结局分类。'),
 code("h=pd.read_csv(ROOT/'data/processed/horizon_availability_current.csv')\nfor group in ['horizon_availability_all_valid_srs','horizon_availability_baseline_mask_cohort']:\n    print(group)\n    print(pd.DataFrame(summary[group]).to_string(index=False))\nassert h.verified_non_event.sum()==0\nassert h.verified_event_free_followup_day.isna().all()"),
 md('## 诊断标签仍未补足\n\n新版有35个数值型坏死时间（29名患者），125个病灶仍未知。35个时间中，32个在所记SRS之后且未晚于死亡，2个早于SRS，1个晚于死亡。时间次序合理不代表诊断依据已经逐例核实。论文报告39个病灶，与新版仍差4个，不能按患者阳性推断其余病灶阳性。'),
 code("c=pd.read_csv(ROOT/'data/processed/clinical_current.csv')\na=pd.read_csv(ROOT/'data/processed/followup_availability_current.csv')\nprint(a.rn_timing_class.value_counts().to_string())\nprint('Unknown RN',c.rn_time_day.isna().sum(),'verified non-events',c.verified_non_event.sum())\nassert c.loc[c.rn_time_day.isna(),'rn_status'].eq('unknown').all()\nprint('Models fitted:',summary['models_fitted'])\nprint('Status:',summary['modeling_status'])")
])
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
nbf.write(nb,root/'notebooks/05_endpoint_versions_and_followup.ipynb')
print('Created Notebook 05')
