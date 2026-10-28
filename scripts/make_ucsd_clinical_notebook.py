"""Generate the approved revised-question clinical baseline Notebook11."""
from pathlib import Path
import sys
import nbformat as nbf
root = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb = nbf.v4.new_notebook(cells=[
    md('# 11 高级别胶质瘤治疗后鉴别：基础临床模型\n\n用户已批准改题及本步基础模型。问题是残余/复发肿瘤与治疗相关改变的探索性鉴别，使用UCSD-PTGBM公开资料；原OpenBTAI脑转移瘤未来RN风险问题仍暂停，两队列不合并。\n\n先阅读固定方案`reports/ucsd_clinical_baseline_protocol.md`。只用年龄和性别，固定5折患者分组、种子20261029、C=1的Logistic回归，无调参。标签1为官方完整分组补集推导的肿瘤，标签0来自51条negative-case清单，不代表逐例病理证实或未来RN阴性。'),
    code("from pathlib import Path\nimport sys, json, hashlib\nimport numpy as np\nimport pandas as pd\nfrom IPython.display import display, Image\nROOT=Path.cwd()\nif ROOT.name=='notebooks': ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.ucsd_clinical_baseline import make_cohort, run, FEATURES\ncohort=make_cohort(ROOT)\nassert len(cohort)==243 and cohort.patient_id.nunique()==178\nassert cohort[FEATURES].notna().all().all()\nprint(cohort.groupby('tumor_label').agg(timepoints=('ID','size'),patients=('patient_id','nunique')))\ndisplay(cohort[cohort.diagnosis_text_anomaly.eq(1)][['ID','primary_diagnosis_raw','age_years','sex_at_birth_raw']])"),
    md('## 纳入与来源异常\n\n保留全部243个时间点。源集合为高级别胶质瘤，包含少量非GBM诊断；一条Grade 5文本原样保留并标记，未作为预测变量。年龄和性别完整。11名患者在不同扫描中跨类，所有扫描留在同一验证折。原始亚型明细与官网介绍的计数差异仍保留，未补造RN。'),
    code("assert cohort.groupby('patient_id').tumor_label.nunique().gt(1).sum()==11\nassert set(FEATURES)=={'age_years','sex_male'}\nsummary=run(ROOT)\nprint('OOF results:',json.dumps(summary['logistic_oof'],indent=2))\nprint('Training-fold prevalence comparator:',json.dumps(summary['prevalence_only_oof'],indent=2))\nprint('Patient-cluster 95% intervals:',json.dumps(summary['patient_cluster_bootstrap_95ci'],indent=2))"),
    md('## 患者分组和折内预处理验证\n\n下面独立核对每折患者不重叠、每个时间点恰有一个OOF概率，以及年龄缩放来自该训练折。对照概率也只来自该训练折，不能使用完整队列的结局比例。'),
    code("d=pd.read_csv(ROOT/'data/processed/ucsd_clinical_oof_predictions.csv')\nfolds=json.loads((ROOT/'reports/ucsd_clinical_baseline/fold_audit.json').read_text())\nassert d.ID.nunique()==len(d)==243\nassert d.groupby('patient_id').validation_fold.nunique().eq(1).all()\nfor f in folds:\n    train=d[d.validation_fold.ne(f['fold'])]; test=d[d.validation_fold.eq(f['fold'])]\n    assert set(train.patient_id).isdisjoint(test.patient_id)\n    assert set(test.patient_id)==set(f['test_patients'])\n    assert np.isclose(train.age_years.mean(),f['train_age_mean'])\n    assert np.isclose(train.age_years.std(ddof=0),f['train_age_sd'])\n    assert np.allclose(test.oof_prevalence_only_probability,train.tumor_label.mean())\ndisplay(pd.read_csv(ROOT/'reports/ucsd_clinical_baseline/fold_metrics.csv'))"),
    md('## 结果可视化\n\nROC、肿瘤类PR曲线和5个分位区间的描述性校准图均基于OOF概率。肿瘤类占比约79%，其AP必须与这一比例同时解释。0.5阈值预先固定，未优化。患者整簇bootstrap 2000次，固定OOF概率；区间不涵盖重新训练和重划折的全部变异。'),
    code("display(Image(filename=str(ROOT/'outputs/ucsd-clinical-baseline-20261029/clinical_baseline_validation.png')))\ndisplay(pd.read_csv(ROOT/'reports/ucsd_clinical_baseline/calibration_bins.csv'))\nassert summary['external_validation'] is False and summary['model_selection_performed'] is False"),
    md('## 最终参数及解释边界\n\n全队列拟合仅保存可复建系数，不用训练集指标替代验证。年龄和性别模型信号即使很弱也如实保留，不通过换种子、阈值或试很多模型来追求高AUC。模型局限包括单中心回顾性样本、推导标签、混合组织学和重复扫描。结果不能表述为外部验证或临床可用模型。\n\n本步没有加入MRI。下一阶段建议先审核新队列MRI获取途径、代表性样本和独立于标签定义的ROI方案；须用户再次批准后执行。'),
    code("display(pd.Series(summary['final_fit_parameters'],dtype=object))\nassert summary['original_OpenBTAI_model_ready'] is False\nassert summary['mri_features_used'] is False\nassert summary['next_step_requires_user_approval'] is True\nassert summary['protocol_sha256']==hashlib.sha256((ROOT/'reports/ucsd_clinical_baseline_protocol.md').read_bytes()).hexdigest()\nprint('Approved clinical baseline finished. Next stage awaits user approval.')"),
])
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
             'language_info':{'name':'python','version':sys.version.split()[0]}}
nbf.write(nb,root/'notebooks/11_ucsd_clinical_baseline.ipynb')
print('Created Notebook11')
