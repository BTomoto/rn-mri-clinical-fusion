"""Build Notebook10: approved public-label feasibility audit only."""
from pathlib import Path
import sys
import nbformat as nbf
root=Path(__file__).resolve().parents[1];md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
nb=nbf.v4.new_notebook(cells=[
 md('# 10 公开标签可行性核查\n\n本轮仅核查能否获得可用结局，不训练模型、不下载新队列MRI，也不自动更改原研究问题。按用户2026-10-29要求，本步结束后汇总结果、失败原因及下一步计划，等待批准再进入下一阶段。模型复杂度和效果可以保守，但不把未知标签补成已证实阴性。'),
 code("from pathlib import Path\nimport sys,json,runpy,hashlib\nimport pandas as pd\nROOT=Path.cwd()\nif ROOT.name=='notebooks':ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nsummary=runpy.run_path(str(ROOT/'scripts/audit_public_label_feasibility.py'))['run']()\nassert summary['models_fitted'] is False\nassert summary['scope_change_approved'] is False"),
 md('## 此前未读取的RN-D3附录\n\n本轮通过Europe PMC公开补充材料接口取得同篇论文附录，核验ZIP与DOCX哈希，提取全部表格文字，并人工检查两张嵌入图。3个表格分别是队列汇总、网络结构和超参数；2张图为训练曲线与ROC。该附录未提供可与现有MOLAB病灶连接的标签表。此前的“附录未核查”缺口已关闭；结论仅限此份已核验文件。'),
 code("supp=json.loads((ROOT/'data/metadata/public_label_audit_20261029/rnd3_supplement_review.json').read_text())\nprint({k:supp[k] for k in ['bundle_sha256','docx_sha256','table_count','embedded_image_count','text_molab_id_pattern_hits','lesion_level_joinable_label_table_observed']})\nassert supp['table_count']==3 and supp['embedded_image_count']==2\nassert supp['previous_access_gap_closed'] is True"),
 md('## UCSD-PTGBM当前公开标签文件\n\n使用官网当前链接的临床v3文件和51条negative-case分类文件。243个扫描时间点来自178名患者，不能当作243名独立患者。源文件中Radiation necrosis实际为7个时间点、4名患者；网站/论文介绍为10个时间点。其他亚型也有差异，原值全部保留，不按介绍补造3条RN。'),
 code("a=pd.read_csv(ROOT/'data/processed/ucsd_ptgbm_label_feasibility.csv')\ncounts=pd.read_csv(ROOT/'data/processed/ucsd_ptgbm_subtype_count_comparison.csv')\nprint(counts.to_string(index=False))\nrn=a[a.negative_list_dx=='Radiation necrosis']\nprint(rn[['ID','patient_id','negative_list_dx','source_row_negative_list']].to_string(index=False))\nassert len(rn)==7 and rn.patient_id.nunique()==4\nassert len(a)==a.ID.nunique()==243\nassert a.patient_id.nunique()==178"),
 md('## 可作为候选的新研究问题\n\n当前51个时间点明确列于治疗相关改变清单；依据作者声明的243=192肿瘤+51治疗相关改变分组，其余192个构成推导的肿瘤候选标签，来源单独标记。51个时间点涉及39名患者，192个涉及150名；11名患者在不同时间点跨两类，因此后续必须按患者分组。此问题是高级别胶质瘤治疗后影像鉴别，不是脑转移瘤将来RN风险。'),
 code("print(a.groupby('broad_tumor_label_candidate').agg(timepoints=('ID','size'),patients=('patient_id','nunique')).to_string())\nprint('Patients with both classes:',a.groupby('patient_id').broad_tumor_label_candidate.nunique().gt(1).sum())\nassert summary['tumor_candidate_timepoints']==192 and summary['treatment_change_timepoints']==51\nassert summary['all_negative_list_ids_match_current_clinical'] is True\nassert a.use_for_model.sum()==a.analysis_question_approved.sum()==0\nassert a.loc[a.negative_list_dx!='Radiation necrosis','rn_status_for_audit'].eq('not_adjudicated_as_RN_negative').all()"),
 md('## 本步结论及待批准计划\n\n原脑转移瘤RN风险模型仍因无事件随访及阴性结局证据缺失而不具备训练条件。单独改做UCSD的RN分类也不建议：实际只有4名明确RN患者，且亚型计数版本不一致。\n\n建议下一步经批准后，将问题改为高级别胶质瘤治疗后“残余/复发肿瘤与治疗相关改变”的探索性鉴别，先核对患者分组与标签，再跑预先指定的基础临床Logistic模型；不以高AUC为目标，不使用未来随访或用于定义标签的肿瘤掩膜体积作输入。加入MRI特征前，另行确认不泄漏标签的ROI与特征方案。本步未执行这项计划。'),
 code("original=pd.read_csv(ROOT/'data/processed/clinical_current.csv')\nassert original.rn_time_day.isna().sum()==125 and original.verified_non_event.sum()==0\nassert summary['original_OpenBTAI_model_ready'] is False\nassert summary['next_step_requires_user_approval'] is True\nassert summary['mri_downloaded_for_new_cohort'] is False\nprint('Feasibility audit complete. No new model fitted; awaiting user approval for the proposed next step.')")
])
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
nbf.write(nb,root/'notebooks/10_public_label_feasibility.ipynb');print('Created Notebook10')
