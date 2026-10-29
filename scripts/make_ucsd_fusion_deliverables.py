"""Create Stage18 figures, typed workbook inputs and a reproducible Notebook."""
from pathlib import Path
import argparse,json,sys
import nbformat as nbf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve,precision_recall_curve
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_fusion import EVALUATED,FEATURES


def generate(root=ROOT):
 root=Path(root);out=root/'reports/ucsd_fusion';figdir=root/'figures/ucsd_fusion';figdir.mkdir(parents=True,exist_ok=True)
 s=json.loads((out/'metrics.json').read_text());d=pd.read_csv(root/'data/processed/ucsd_fusion_oof.csv')
 metrics=pd.read_csv(out/'model_metrics.csv');pairs=pd.read_csv(out/'paired_comparisons.csv');bins=pd.read_csv(out/'calibration_bins.csv')
 palette={'M0':'#8997A1','M1':'#35556D','MRI':'#AA7544','Fusion':'#507E63'}
 labels={'M0':'Age + sex','M1':'Clinical','MRI':'MRI (8 features)','Fusion':'Clinical + MRI'}
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
 def save(fig,name):
  for ext in ['png','pdf']:
   dest=figdir/(name+'.'+ext);part=dest.with_name(dest.name+'.partial');fig.savefig(part,format=ext,dpi=180);part.replace(dest)
  plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(13.8,4.3),layout='constrained');y=d.tumor_label
 for name,color in palette.items():
  p=d[name+'_oof_probability'];fpr,tpr,_=roc_curve(y,p);precision,recall,_=precision_recall_curve(1-y,1-p)
  axes[0].plot(fpr,tpr,color=color,label=f'{labels[name]}: {s["metrics"][name]["roc_auc"]:.3f}')
  axes[1].plot(recall,precision,color=color,label=f'{labels[name]}: {s["metrics"][name]["ap_treatment_change"]:.3f}')
  b=bins[bins.model.eq(name)];axes[2].plot(b.mean_predicted,b.observed_tumor,'o-',color=color,label=labels[name],markersize=4)
 axes[0].plot([0,1],[0,1],'--',color='#ABB4BB',lw=1)
 axes[1].axhline(float((1-y).mean()),ls='--',color='#ABB4BB',lw=1,label='Treatment-change prevalence')
 axes[2].plot([0,1],[0,1],'--',color='#ABB4BB',lw=1)
 for ax in axes:ax.set(xlim=(0,1),ylim=(0,1));ax.legend(fontsize=7.7,loc='lower right' if ax is axes[0] else 'upper right' if ax is axes[1] else 'upper left')
 axes[0].set(title='Patient-grouped OOF ROC',xlabel='False positive rate',ylabel='Tumor sensitivity')
 axes[1].set(title='Treatment-change precision-recall',xlabel='Treatment-change recall',ylabel='Treatment-change precision')
 axes[2].set(title='Descriptive OOF calibration',xlabel='Predicted tumor probability',ylabel='Observed tumor proportion')
 save(fig,'model_comparison')
 fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
 mm=metrics[metrics.model.isin(EVALUATED)].set_index('model').loc[EVALUATED].reset_index()
 for k,row in mm.iterrows():
  axes[0].errorbar(row.roc_auc,k,xerr=[[row.roc_auc-row.roc_auc_ci_lower],[row.roc_auc_ci_upper-row.roc_auc]],fmt='o',color=palette.get(row.model.removesuffix('_eroded'),'#35556D'),capsize=3)
 axes[0].set_yticks(range(len(mm)),['Age + sex','Clinical','MRI','Fusion','Eroded MRI','Eroded fusion']);axes[0].invert_yaxis();axes[0].set(xlim=(0,1),xlabel='OOF AUC and patient-bootstrap 95% interval',title='Original and eroded ROI')
 cmp=pairs[pairs.metric.eq('roc_auc')].reset_index(drop=True)
 for k,row in cmp.iterrows():axes[1].errorbar(row.difference,k,xerr=[[row.difference-row.lower],[row.upper-row.difference]],fmt='o',color='#507E63' if row.primary_comparison else '#788994',capsize=3)
 axes[1].set_yticks(range(len(cmp)),['Fusion minus clinical','MRI minus clinical','Clinical minus age/sex','Eroded fusion minus clinical','Eroded minus original fusion']);axes[1].invert_yaxis();axes[1].axvline(0,ls='--',color='#ABB4BB');axes[1].set(xlabel='Paired AUC difference and 95% interval',title='Prespecified comparisons')
 save(fig,'paired_and_boundary_comparison')
 def dataset(frame):return dict(headers=frame.columns.tolist(),rows=json.loads(frame.to_json(orient='values',force_ascii=False,double_precision=15)))
 first=['model','roc_auc','roc_auc_ci_lower','roc_auc_ci_upper','brier','specificity_treatment_change','tn','fp','fn','tp','ap_treatment_change','sensitivity_tumor']
 metric_export=metrics[first+[c for c in metrics if c not in first]]
 summary_inputs=dict(summary=s,datasets={
  'Metrics':dataset(metric_export),'Comparisons':dataset(pairs),'OOF':dataset(d),
  'Inputs':dataset(pd.read_csv(root/'data/processed/ucsd_clinical_image_features.csv')),
  'Eroded':dataset(pd.read_csv(root/'data/processed/ucsd_image_features_eroded.csv')),
  'Folds':dataset(pd.read_csv(out/'fold_metrics.csv')),'Calibration':dataset(bins),
  'Coefficients':dataset(pd.read_csv(out/'full_fit_coefficients.csv'))},
  source_note='Source: frozen Stage17 UCSD-PTGBM clinical/image features; DOI 10.7937/fwv2-dt74; https://github.com/data-nih/tcia/releases. Outcomes and MRI features are unchanged. analysis_lock.json records input hashes; protocol fixes patient-grouped five-fold validation.')
 (root/'reports/ucsd_fusion_workbook_input.json').write_text(json.dumps(summary_inputs,ensure_ascii=False,allow_nan=False))
 return metrics,pairs


def notebook(root=ROOT):
 md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
 cells=[md('# 第18步：共同病例临床、MRI及融合Logistic模型\n\n182次扫描/135名患者，肿瘤141次、治疗改变41次。固定4个主模型、同一套患者分组5折，唯一主要比较为Fusion−M1的AUC差。无调参、特征筛选或阈值优化。源标注盲法未确认，8位强度、未知空间单位及公开标签来源限制延续。'),
 code("from pathlib import Path\nimport sys,json\nimport pandas as pd,numpy as np\nROOT=Path.cwd()\nif not (ROOT/'src').exists(): ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.ucsd_fusion import freeze_plan,run,FEATURES\nd,eroded,folds,lock=freeze_plan(ROOT)\nprint(folds.groupby('validation_fold').agg(scans=('ID','size'),patients=('patient_id','nunique'),tumor=('tumor_label','sum')))\nprint('Fixed model inputs:',json.dumps(FEATURES,ensure_ascii=False))\nprint('Input and protocol lock:',json.dumps(lock,indent=2))"),
 md('只在训练折拟合填补及标准化。MRI敏感性整体替换为一次腐蚀特征，同病例同折。2,000次患者聚类配对bootstrap固定已有OOF概率，不重拟合训练过程。区间不覆盖全部训练/分折变异。'),
 code("summary=run(ROOT)\nprint('Bootstrap valid / attempted:',summary['bootstrap_valid'],summary['bootstrap_attempts'])\nprint('Patient / BraTS-patient overlap:',summary['patient_overlap'],summary['brats_patient_overlap'])\nprint('No tuning:',not summary['hyperparameter_search'])"),
 code("out=ROOT/'reports/ucsd_fusion'\nmetrics=pd.read_csv(out/'model_metrics.csv');comparisons=pd.read_csv(out/'paired_comparisons.csv')\nprint(metrics[['model','roc_auc','roc_auc_ci_lower','roc_auc_ci_upper','brier','ap_treatment_change','tn','fp','fn','tp']].to_string(index=False))\nprint(comparisons.to_string(index=False))\nprint('Calibration:',json.dumps(summary['calibration'],indent=2))"),
 code("import importlib.util\nspec=importlib.util.spec_from_file_location('fusion_deliverables',ROOT/'scripts/make_ucsd_fusion_deliverables.py')\nmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\nmodule.generate(ROOT)\nfrom IPython.display import display,Image\ndisplay(Image(filename=str(ROOT/'figures/ucsd_fusion/model_comparison.png')))\ndisplay(Image(filename=str(ROOT/'figures/ucsd_fusion/paired_and_boundary_comparison.png')))"),
 code("import hashlib\npred=pd.read_csv(ROOT/'data/processed/ucsd_fusion_oof.csv')\nassert len(pred)==182 and pred.ID.is_unique\nfor key in ['patient_id','brats_patient_id','validation_group']:\n    assert pred.groupby(key).validation_fold.nunique().eq(1).all()\nfor p,h in lock['input_sha256'].items():\n    assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h\nassert hashlib.sha256((ROOT/'reports/ucsd_fusion_protocol.md').read_bytes()).hexdigest()==lock['protocol_sha256']\nassert hashlib.sha256((ROOT/'src/rn_public/ucsd_fusion.py').read_bytes()).hexdigest()==lock['analysis_code_sha256']\nprint('Input bytes, fixed folds and model code verified. Prior-stage results preserved.')\nprint('Full-cohort coefficients describe fitted models; all displayed performance uses OOF predictions.')"),
 md('本阶段到此结束。报告全部固定模型及腐蚀敏感性，不根据较高AUC改写主分析。内部验证、有限病例与分割来源限制使结果不能直接解释为临床可用；后续工作等待用户批准。')]
 nbf.write(nbf.v4.new_notebook(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'))),root/'notebooks/18_ucsd_clinical_mri_fusion.ipynb')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--notebook-only',action='store_true');a=p.parse_args()
 if a.notebook_only:notebook()
 else:
  metrics,pairs=generate();print(metrics.to_string(index=False))
