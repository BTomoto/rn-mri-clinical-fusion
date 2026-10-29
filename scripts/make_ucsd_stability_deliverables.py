"""Stage19 descriptive stability figures, workbook inputs and executable Notebook."""
from pathlib import Path
import argparse,json,sys
import nbformat as nbf
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_stability import MODELS


def generate(root=ROOT):
 root=Path(root);out=root/'reports/ucsd_stability';figdir=root/'figures/ucsd_stability';figdir.mkdir(parents=True,exist_ok=True)
 s=json.loads((out/'metrics.json').read_text());m=pd.read_csv(out/'repeated_metrics.csv');delta=pd.read_csv(out/'repeated_paired_differences.csv')
 single=pd.read_csv(out/'single_scan_metrics.csv');palette={'M0':'#8997A1','M1':'#35556D','MRI':'#AA7544','Fusion':'#507E63'}
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
 def save(fig,name):
  for ext in ['png','pdf']:
   dest=figdir/(name+'.'+ext);part=dest.with_name(dest.name+'.partial');fig.savefig(part,format=ext,dpi=180);part.replace(dest)
  plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11.5,4.3),layout='constrained')
 for name,color in palette.items():
  a=m[m.model.eq(name)];axes[0].plot(a['repeat'],a.roc_auc,'o-',color=color,markersize=3,label=name)
 axes[0].set(xlabel='Prespecified repeat',ylabel='Pooled OOF AUC within repeat',ylim=(0,1),title='Same 182 scans, 20 fixed patient-grouped splits');axes[0].legend(fontsize=8,ncol=2);axes[0].set_xticks([1,5,10,15,20])
 d=delta[delta.metric.eq('roc_auc')];axes[1].plot(d['repeat'],d.difference,'o-',color='#507E63',markersize=4)
 axes[1].axhline(0,color='#ABB4BB',ls='--');axes[1].set(xlabel='Prespecified repeat',ylabel='Fusion minus clinical OOF AUC',title='Paired split differences, not independent studies');axes[1].set_xticks([1,5,10,15,20])
 save(fig,'repeated_validation')
 fig,axes=plt.subplots(1,2,figsize=(10.8,4.2),layout='constrained')
 for k,name in enumerate(MODELS):
  row=single[single.model.eq(name)].iloc[0]
  axes[0].errorbar(row.roc_auc,k,xerr=[[row.roc_auc-row.roc_auc_ci_lower],[row.roc_auc_ci_upper-row.roc_auc]],fmt='o',color=palette[name],capsize=3)
  axes[1].bar(k,row.specificity_treatment_change,color=palette[name]);axes[1].text(k,row.specificity_treatment_change+.025,f'{int(row.tn)}/{s["single_scan"]["treatment_change_scans"]}',ha='center',fontsize=9)
 axes[0].set_yticks(range(4),list(MODELS));axes[0].invert_yaxis();axes[0].set(xlim=(0,1),xlabel='OOF AUC with patient-bootstrap 95% interval',title=f'One available scan per patient (n={s["single_scan"]["scans"]})')
 axes[1].set_xticks(range(4),list(MODELS));axes[1].set(ylim=(0,1),ylabel='Treatment-change recall at tumor p < 0.5',title='Fixed threshold in the selected-scan cohort')
 save(fig,'single_scan_sensitivity')
 def dataset(frame):return dict(headers=frame.columns.tolist(),rows=json.loads(frame.to_json(orient='values',force_ascii=False,double_precision=15)))
 distributions=pd.read_csv(out/'repeated_metric_distribution.csv')
 input_data=pd.read_csv(root/'data/processed/ucsd_clinical_image_features.csv')
 selected=pd.read_csv(out/'single_scan_selection.csv')
 cases=input_data.merge(selected[['ID','session_number','selected','reason']],on='ID',validate='one_to_one')
 datasets={
  'RepeatMetrics':dataset(m.sort_values(['model','repeat']).reset_index(drop=True)),
  'RepeatDeltas':dataset(delta.sort_values(['metric','repeat']).reset_index(drop=True)),'SingleMetrics':dataset(single),
  'Cases':dataset(cases[['ID','patient_id','tumor_label','session_number','selected','reason',*[x for x in cases if x not in ['ID','patient_id','tumor_label','session_number','selected','reason']]]]),
  'SingleOOF':dataset(pd.read_csv(root/'data/processed/ucsd_stability_single_scan_oof.csv')),
  'RepeatedOOF':dataset(pd.read_csv(root/'data/processed/ucsd_stability_repeated_oof.csv')),
  'RepeatStatus':dataset(pd.read_csv(out/'repeat_status.csv'))}
 payload=dict(summary=s,datasets=datasets,source_note='Frozen Stage17/18 UCSD-PTGBM data and model definitions; DOI 10.7937/fwv2-dt74. No feature or label changes. analysis_lock.json pins inputs and all case/fold manifests. Single-scan selection uses minimum numeric available session, not clinical first visit.')
 (root/'reports/ucsd_stability_workbook_input.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False))
 return distributions,single


def notebook(root=ROOT):
 md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
 cells=[md('# 第19步：固定模型的分折稳定性与单扫描敏感性\n\n沿用第18步四个原ROI模型，不调参、不选特征、不优化阈值。固定20套患者分组五折，保留全部结果；重复共用患者，分布不是独立样本或置信区间。每患者单扫描按现有影像中最小数字会话编号选取，不称首次就诊。'),
 code("from pathlib import Path\nimport sys,json\nimport pandas as pd,numpy as np\nROOT=Path.cwd()\nif not (ROOT/'src').exists(): ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.ucsd_stability import freeze_plan,run,MODELS,SEEDS\nd,single,manifest,plans,sm,sp,lock=freeze_plan(ROOT)\nprint('Fixed seeds:',SEEDS)\nprint('Repeated manifest rows:',len(manifest))\nprint('Selected scans / patients:',len(single),single.patient_id.nunique())\nprint('Selected labels:',single.tumor_label.value_counts().to_dict())\nprint('Invalid frozen folds:',sum(not f['valid'] for p in plans for f in p['folds'])+sum(not f['valid'] for f in sp))"),
 code("summary=run(ROOT)\nprint('Complete / failed repeats:',summary['repeats_complete'],summary['repeats_failed'])\nprint('Stage18 anchor maximum probability difference:',summary['anchor_maximum_probability_difference'])\nprint('Single-scan complete:',summary['single_scan']['complete'])\nprint('Single-scan bootstrap valid:',summary['single_scan']['bootstrap_valid'])"),
 md('每套OOF指标先在该套完整扫描中计算，再描述20套指标分布。不合并为3,640个独立病例。单扫描人群及结局分布变化，不能与182条主结果直接作增量比较。其患者bootstrap固定OOF概率，不包含全部训练变异。'),
 code("out=ROOT/'reports/ucsd_stability'\nmetric_distribution=pd.read_csv(out/'repeated_metric_distribution.csv')\nprint(metric_distribution[metric_distribution.metric.isin(['roc_auc','brier','specificity_treatment_change'])].to_string(index=False))\nprint(pd.read_csv(out/'repeated_delta_distribution.csv').to_string(index=False))\nprint(pd.read_csv(out/'single_scan_metrics.csv')[['model','roc_auc','roc_auc_ci_lower','roc_auc_ci_upper','brier','tn','fp','fn','tp','calibration_slope']].to_string(index=False))\nprint('Single-scan paired differences:',json.dumps(summary['single_scan']['paired_differences'],indent=2))\nprint('Single-scan paired intervals:',json.dumps({k:v for k,v in summary['single_scan']['bootstrap_95ci'].items() if 'minus' in k},indent=2))"),
 code("import importlib.util\nspec=importlib.util.spec_from_file_location('stability_deliverables',ROOT/'scripts/make_ucsd_stability_deliverables.py')\nmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\nmodule.generate(ROOT)\nfrom IPython.display import display,Image\ndisplay(Image(filename=str(ROOT/'figures/ucsd_stability/repeated_validation.png')))\ndisplay(Image(filename=str(ROOT/'figures/ucsd_stability/single_scan_sensitivity.png')))"),
 code("import hashlib\nfor p,h in lock['input_sha256'].items():\n    assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h\nassert hashlib.sha256((ROOT/'reports/ucsd_stability_protocol.md').read_bytes()).hexdigest()==lock['protocol_sha256']\nassert hashlib.sha256((ROOT/'src/rn_public/ucsd_stability.py').read_bytes()).hexdigest()==lock['analysis_code_sha256']\nrepeated=pd.read_csv(ROOT/'data/processed/ucsd_stability_repeated_oof.csv')\nfor _,frame in repeated.groupby('repeat'):\n    assert frame.ID.is_unique and len(frame)==182\n    for key in ['patient_id','brats_patient_id','validation_group']:\n        assert frame.groupby(key).validation_fold.nunique().eq(1).all()\nassert not summary['prior_primary_analysis_replaced']\nprint('Frozen inputs, code and patient isolation verified; no independent-repeat confidence claim.')"),
 md('保留第18步为原主分析。完整结果、失败次数和局限均需报告，不选择最高重复替代主结果。此阶段结束后等待用户批准论文材料整理。')]
 nbf.write(nbf.v4.new_notebook(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'))),root/'notebooks/19_ucsd_model_stability.ipynb')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--notebook-only',action='store_true');a=p.parse_args()
 if a.notebook_only:notebook()
 else:generate()
