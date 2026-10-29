"""Stage20 tables and figures from frozen results; no model fit or manuscript prose."""
from pathlib import Path
import argparse,hashlib,json,sys
import nbformat as nbf
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from sklearn.metrics import roc_curve,precision_recall_curve
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))

MODELS=['M0','M1','MRI','Fusion']
LABELS={'M0':'年龄＋性别','M1':'扩展临床','MRI':'MRI八项','Fusion':'临床＋MRI','MRI_eroded':'腐蚀MRI','Fusion_eroded':'腐蚀融合'}
INPUTS=['data/processed/ucsd_clinical_revalidated_cohort.csv','data/processed/ucsd_clinical_image_features.csv',
 'data/processed/ucsd_fusion_oof.csv','reports/ucsd_fusion/metrics.json','reports/ucsd_fusion/calibration_bins.csv',
 'reports/ucsd_fusion/paired_comparisons.csv','reports/ucsd_stability/metrics.json',
 'reports/ucsd_stability/repeated_metrics.csv','reports/ucsd_stability/repeated_metric_distribution.csv',
 'reports/ucsd_stability/repeated_delta_distribution.csv','reports/ucsd_stability/single_scan_metrics.csv',
 'reports/ucsd_batch_features/feature_dictionary.csv','data/raw/reference/ucsd_ptgbm_clinical_v3.xlsx',
 'reports/ucsd_clinical_revalidation/excluded_identity_conflicts.csv']


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def baseline(groups,table_id):
 rows=[];numbers=[]
 for field,label,kind in [('scans','扫描记录数','n'),('patients','源患者数','patients'),
  ('age_years','年龄，岁','continuous'),('sex_male','男性','binary'),
  ('tumor_label','肿瘤扫描','binary'),('treatment_change','治疗改变扫描','binary'),
  ('days_since_initial_event','距初始事件天数，已知记录','continuous'),
  ('interval_observed','间隔已知记录','binary'),('initial_event_missing','间隔缺失记录','binary'),
  ('other_treatment_prior','扫描前其他治疗','binary')]:
  cells=[label]
  for name,d in groups.items():
   r=dict(table_id=table_id,cohort=name,variable=field,statistic=kind,scan_denominator=len(d),
    patient_count=int(d.patient_id.nunique()),observed_n=None,count=None,percent=None,median=None,q25=None,q75=None)
   if kind in ['n','patients']:
    count=len(d) if kind=='n' else d.patient_id.nunique();cells.append(int(count));r['count']=int(count)
   elif kind=='continuous':
    a=d[field].dropna();q=a.quantile([.25,.5,.75]);r.update(observed_n=len(a),median=float(q.loc[.5]),q25=float(q.loc[.25]),q75=float(q.loc[.75]))
    cells.append(f'{q.loc[.5]:.1f} [{q.loc[.25]:.1f}, {q.loc[.75]:.1f}]')
   else:
    a=1-d.tumor_label if field=='treatment_change' else d.initial_event_missing.eq(0) if field=='interval_observed' else d[field]
    count=int(a.sum());pct=100*count/len(d);r.update(observed_n=len(d),count=count,percent=pct);cells.append(f'{count}/{len(d)} ({pct:.1f}%)')
   numbers.append(r)
  rows.append(cells)
 return pd.DataFrame(rows,columns=['指标',*groups]),numbers


def generate(root=ROOT):
 root=Path(root);out=root/'reports/ucsd_paper_materials';tables=root/'outputs/ucsd-paper-materials-20261029/tables';figdir=root/'outputs/ucsd-paper-materials-20261029/figures'
 out.mkdir(parents=True,exist_ok=True);tables.mkdir(parents=True,exist_ok=True);figdir.mkdir(parents=True,exist_ok=True)
 hashes={p:digest(root/p) for p in INPUTS}
 c=pd.read_csv(root/INPUTS[0]);d=pd.read_csv(root/INPUTS[1]);main=json.loads((root/'reports/ucsd_fusion/metrics.json').read_text());stable=json.loads((root/'reports/ucsd_stability/metrics.json').read_text())
 if (len(c),c.patient_id.nunique(),len(d),d.patient_id.nunique())!=(238,176,182,135):raise ValueError('frozen_cohort_changed')
 raw=pd.read_excel(root/'data/raw/reference/ucsd_ptgbm_clinical_v3.xlsx',sheet_name='Cinical info')
 excluded=pd.read_csv(root/'reports/ucsd_clinical_revalidation/excluded_identity_conflicts.csv')
 if (len(raw),raw.ID.str.rsplit('_',n=1).str[0].nunique(),len(excluded),excluded.patient_id.nunique())!=(243,178,5,2):raise ValueError('source_flow_counts_changed')
 specs=[];numeric=[]
 def add(key,title,frame,notes):
  frame.to_csv(tables/(key+'.csv'),index=False)
  specs.append(dict(key=key,title=title,headers=frame.columns.tolist(),rows=json.loads(frame.to_json(orient='values',force_ascii=False,double_precision=15)),notes=notes))
 t,nn=baseline({'全部影像扫描':d,'肿瘤扫描':d[d.tumor_label.eq(1)],'治疗改变扫描':d[d.tumor_label.eq(0)]},'Table1');numeric+=nn
 add('Table1','表1 主影像队列的临床特征',t,['连续变量为中位数 [Q1, Q3]。百分比的分母为该列扫描数，不是去重患者数。',
  '两类扫描按患者去重为114和29名，其中8名患者在不同扫描出现两类标签，因此不能相加为总患者数。',
  '初始事件为源表记录的初始手术、治疗或诊断事件，非统一放疗日期。间隔描述仅使用已知记录，未填补。'])
 mm=pd.read_csv(root/'reports/ucsd_fusion/model_metrics.csv');mm=mm.set_index('model')
 def performance(names,source):
  return pd.DataFrame([dict(模型=LABELS[n],AUC=source.loc[n,'roc_auc'],CI_lower=source.loc[n,'roc_auc_ci_lower'],CI_upper=source.loc[n,'roc_auc_ci_upper'],Brier=source.loc[n,'brier'],AP_TC=source.loc[n,'ap_treatment_change'],TC_correct=int(source.loc[n,'tn']),TC_total=41 if source is mm else 22) for n in names])
 ci_note='95%区间为2,000次患者配对bootstrap百分位区间，固定OOF概率，未重拟合模型，不涵盖全部训练和分折变异。'
 add('Table2','表2 主分析的患者分组OOF性能',performance(MODELS,mm),[ci_note,'AP_TC为治疗改变的平均精确率，使用1减肿瘤概率计算。主队列治疗改变比例为41/182。'])
 pairs=pd.read_csv(root/'reports/ucsd_fusion/paired_comparisons.csv');p=pairs[pairs.comparison.eq('Fusion_minus_M1')].copy()
 metric_labels={'roc_auc':'AUC差','ap_treatment_change':'治疗改变AP差','brier':'Brier差','log_loss':'Log loss差'}
 add('Table3','表3 融合相对临床的预设增量比较',pd.DataFrame([dict(指标=metric_labels[r.metric],差值=r.difference,CI_lower=r.lower,CI_upper=r.upper) for r in p.itertuples()]),['差值为Fusion减M1。AUC差是唯一主要比较；其他指标辅助描述。Brier和log loss负差值较好。',ci_note])
 t,nn=baseline({'临床全集':c,'影像覆盖':d,'影像未覆盖':c[~c.ID.isin(d.ID)]},'TableS1');numeric+=nn
 uncovered=c[~c.ID.isin(d.ID)];overlap=set(d.patient_id)&set(uncovered.patient_id)
 if overlap:raise ValueError('unexpected_patient_overlap_between_coverage_groups')
 add('TableS1','表S1 临床队列与当前镜像覆盖情况',t,['各列按扫描记录描述，源患者数逐列去重。本数据中覆盖135名与未覆盖41名患者无交叉。未进行组间显著性检验。'])
 definitions=[['age_years','年龄','M0 M1 Fusion','训练折标准化；岁'],['sex_male','男性标记','M0 M1 Fusion','男性1，女性0；不缩放'],
  ['log_initial_event_days','初始事件间隔','M1 Fusion','log1p天数；折内中位数填补及标准化'],['other_treatment_prior','扫描前其他治疗','M1 Fusion','是1，否0；不缩放'],['initial_event_missing','间隔缺失标记','M1 Fusion','缺失1；不缩放']]
 for seq in ['FLAIR','T1post']:
  for key,label,unit in [('mean','均值','无单位'),('std','标准差','无单位，ddof=0'),('entropy','熵','bit，固定32箱'),('glcm_contrast','GLCM对比度','箱索引差平方，13方向对称合并')]:
   definitions.append([seq+'_'+key,seq+' '+label,'MRI Fusion',unit+'；训练折标准化'])
 add('TableS2','表S2 固定模型变量及处理',pd.DataFrame(definitions,columns=['变量','含义','纳入模型','处理与单位']),[
  '所有Logistic固定L2、C=1、lbfgs、max_iter=2000、class_weight=None。没有调参、筛特征或优化阈值。',
  'MRI先按每图非零正值支持区p1/p99线性缩放，不裁切；源标注全部正标签并集。图像为uint8，空间单位unknown，不计算mL体积、毫米形态或定量ADC。',
  '源日期偏移仅负值取相反数为正间隔；源偏移为0、正值或Unknown记缺失。表中使用已冻结的正天数或缺失。'])
 threshold=[]
 for n in MODELS:
  m=main['metrics'][n];q=main['calibration'][n]
  threshold.append(dict(模型=LABELS[n],TC_correct=m['tn'],TC_total=41,Tumor_correct=m['tp'],Tumor_total=141,Balanced_accuracy=m['balanced_accuracy'],Calibration_offset=q['calibration_intercept_offset'],Calibration_slope=q['calibration_slope']))
 add('TableS3','表S3 固定阈值识别与描述性校准',pd.DataFrame(threshold),['固定肿瘤概率≥0.5判肿瘤，<0.5判治疗改变。校准截距采用斜率1的logit概率offset；斜率来自带自由截距的未惩罚回归，仅作描述，不重新校准预测。'])
 add('TableS4','表S4 原标注区域与腐蚀边界敏感性',performance(['MRI','Fusion','MRI_eroded','Fusion_eroded'],mm),[
  '同病例、同折、同参数，腐蚀版本整体替换8项MRI特征。原ROI仍为主分析，不选择较高版本。',
  '腐蚀Fusion减原Fusion的AUC差0.0062，95%区间−0.0051至0.0183。'+ci_note])
 dist=pd.read_csv(root/'reports/ucsd_stability/repeated_metric_distribution.csv').set_index(['model','metric'])
 add('TableS5A','表S5A 二十套固定患者分组验证的分布',pd.DataFrame([dict(模型=LABELS[n],AUC_median=dist.loc[(n,'roc_auc'),'median'],AUC_q25=dist.loc[(n,'roc_auc'),'q25'],AUC_q75=dist.loc[(n,'roc_auc'),'q75'],AUC_min=dist.loc[(n,'roc_auc'),'minimum'],AUC_max=dist.loc[(n,'roc_auc'),'maximum'],Brier_median=dist.loc[(n,'brier'),'median']) for n in MODELS]),[
  '20套全部完整，同一批182次扫描反复分折。范围和四分位数不是95%置信区间，重复不是独立研究。主分析融合AUC为0.7819。'])
 delta=pd.read_csv(root/'reports/ucsd_stability/repeated_delta_distribution.csv')
 add('TableS5B','表S5B 重复验证中融合减临床的差值',pd.DataFrame([dict(指标=metric_labels[r.metric],Median=r.median,Q25=r.q25,Q75=r.q75,Minimum=r.minimum,Maximum=r.maximum,Favourable_repeats=r.negative_count if r.metric in ['brier','log_loss'] else r.positive_count,Total_repeats=20) for r in delta.itertuples()]),['有利方向：AUC及AP为正，Brier及log loss为负。20/20只描述点估计方向，不构成独立重复的显著性检验。'])
 sm=pd.read_csv(root/'reports/ucsd_stability/single_scan_metrics.csv').set_index('model')
 add('TableS6','表S6 每患者单扫描敏感性性能',performance(MODELS,sm),[
  '135条扫描，113次肿瘤、22次治疗改变。选择当前影像中最小数字会话编号，不称首次就诊。与182条主分析人群不同，不直接比较跨人群增量。',ci_note])
 ss=stable['single_scan']
 add('TableS7','表S7 单扫描人群中融合减临床的差值',pd.DataFrame([dict(指标=metric_labels[k],差值=ss['paired_differences'][k],CI_lower=ss['bootstrap_95ci']['Fusion_minus_M1__'+k]['lower'],CI_upper=ss['bootstrap_95ci']['Fusion_minus_M1__'+k]['upper']) for k in metric_labels]),['135条相同病例及折内模型配对。AUC、AP和Brier差的区间均跨零。',ci_note])
 numbers=pd.DataFrame(numeric);numbers.to_csv(tables/'baseline_numeric_details.csv',index=False)
 make_figures(root,figdir,main,stable)
 sources=dict(data_collection='UCSD-PTGBM',data_DOI='10.7937/fwv2-dt74',descriptor_DOI='10.1038/s41597-025-06499-z',mirror='https://github.com/data-nih/tcia/releases',license='CC BY 4.0',label_note='Treatment change from explicit negative list; tumor from frozen published partition complement. Not all pathology confirmed.',source_annotation_blinding_confirmed=False)
 package=dict(tables=specs,baseline_numeric=dict(headers=numbers.columns.tolist(),rows=json.loads(numbers.to_json(orient='values',double_precision=15))),sources=sources,
  figures=['Figure1_Cohort_Flow','Figure2_Main_Comparison','Figure3_Repeat_Stability','FigureS1_Boundary_Sensitivity','FigureS2_Single_Scan'],
  manuscript_body_drafted=False,models_refitted=False,input_sha256=hashes)
 (out/'table_package.json').write_text(json.dumps(package,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 files=[*tables.glob('*.csv'),*[p for p in figdir.iterdir() if p.suffix in ['.png','.pdf','.svg']]]
 receipt=dict(step=20,date='2026-10-29',table_count=len(specs),figure_count=5,figure_png_dpi=600,
  source_inputs_unchanged=all(digest(root/p)==h for p,h in hashes.items()),model_refits=0,new_hypothesis_tests=0,
  manuscript_body_drafted=False,awaiting_user_writing_instructions=True,
  input_sha256=hashes,output_sha256={str(p.relative_to(root)):digest(p) for p in files},analysis_code_sha256=digest(Path(__file__)))
 (out/'generation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return package


def make_figures(root,figdir,main,stable):
 plt.rcParams.update({'font.family':'Nimbus Roman','font.size':10,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
 colors={'M0':'#8997A1','M1':'#35556D','MRI':'#AA7544','Fusion':'#507E63'}
 def save(fig,name):
  for ext in ['png','pdf','svg']:
   path=figdir/(name+'.'+ext);part=path.with_name(path.name+'.partial');fig.savefig(part,format=ext,dpi=600);part.replace(path)
   if ext=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
  plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,7));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
 def box(x,y,w,h,text,fill='#F3F5F7'):
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.007',facecolor=fill,edgecolor='#687B89',linewidth=.8));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=10)
 def arrow(a,b):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=11,color='#687B89',lw=.9))
 box(.19,.86,.62,.10,'Public UCSD-PTGBM clinical records\n243 scans / 178 source patients')
 box(.66,.70,.31,.09,'Dual-ID conflicts excluded\n5 scans / 2 source patients');arrow((.55,.86),(.78,.79))
 box(.05,.68,.54,.11,'Revalidated clinical cohort\n238 scans / 176 source patients');arrow((.36,.86),(.32,.79))
 box(.67,.50,.30,.10,'Not covered by mirror\n56 scans retained in status ledger');arrow((.48,.68),(.78,.60))
 box(.05,.47,.54,.13,'Complete three-file MRI set\n182 scans / 135 source patients\n141 tumor / 41 treatment change');arrow((.32,.68),(.32,.60))
 box(.05,.25,.54,.13,'Primary patient-grouped five-fold analysis\n182 scans; four fixed models\n20 prespecified split repetitions');arrow((.32,.47),(.32,.38))
 box(.65,.24,.32,.15,'Single-scan sensitivity\n135 scans / 135 patients\n113 tumor / 22 treatment change');arrow((.59,.51),(.81,.39))
 ax.text(.5,.10,'Single-scan rule: lowest numeric session in the available MRI subset.\nThis does not establish the true first clinical visit. No external validation.',ha='center',va='center',fontsize=9)
 save(fig,'Figure1_Cohort_Flow')
 pred=pd.read_csv(root/'data/processed/ucsd_fusion_oof.csv');cal=pd.read_csv(root/'reports/ucsd_fusion/calibration_bins.csv');y=pred.tumor_label
 fig,axes=plt.subplots(1,3,figsize=(12.5,4),layout='constrained')
 for name,color in colors.items():
  p=pred[name+'_oof_probability'];x,z,_=roc_curve(y,p);pp,rr,_=precision_recall_curve(1-y,1-p)
  axes[0].plot(x,z,color=color,label=f'{name}: {main["metrics"][name]["roc_auc"]:.3f}')
  axes[1].plot(rr,pp,color=color,label=f'{name}: AP={main["metrics"][name]["ap_treatment_change"]:.3f}')
  b=cal[cal.model.eq(name)];axes[2].plot(b.mean_predicted,b.observed_tumor,'o-',color=color,label=name,markersize=4)
 for ax in [axes[0],axes[2]]:ax.plot([0,1],[0,1],'--',color='#ABB4BB',lw=.8)
 axes[1].axhline((1-y).mean(),ls='--',color='#ABB4BB',label='Treatment-change prevalence')
 for i,ax in enumerate(axes):ax.set(xlim=(0,1),ylim=(0,1));ax.legend(fontsize=8,loc='lower right' if i==0 else 'upper right' if i==1 else 'upper left')
 axes[0].set(title='A  Patient-grouped OOF ROC',xlabel='False positive rate',ylabel='Tumor sensitivity')
 axes[1].set(title='B  Treatment-change PR',xlabel='Treatment-change recall',ylabel='Treatment-change precision')
 axes[2].set(title='C  Descriptive OOF calibration',xlabel='Predicted tumor probability',ylabel='Observed tumor proportion')
 save(fig,'Figure2_Main_Comparison')
 rm=pd.read_csv(root/'reports/ucsd_stability/repeated_metrics.csv');delta=pd.read_csv(root/'reports/ucsd_stability/repeated_paired_differences.csv')
 fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
 for n,color in colors.items():
  a=rm[rm.model.eq(n)];axes[0].plot(a['repeat'],a.roc_auc,'o-',color=color,markersize=3,label=n)
 axes[0].set(xlabel='Prespecified repeat',ylabel='Within-repeat pooled OOF AUC',ylim=(0,1),title='A  Twenty fixed patient-grouped splits');axes[0].legend(fontsize=8,ncol=2)
 a=delta[delta.metric.eq('roc_auc')];axes[1].plot(a['repeat'],a.difference,'o-',color=colors['Fusion'],markersize=3);axes[1].axhline(0,ls='--',color='#ABB4BB');axes[1].set(xlabel='Prespecified repeat',ylabel='Fusion minus clinical AUC',title='B  Paired differences within each split')
 for ax in axes:ax.set_xticks([1,5,10,15,20])
 save(fig,'Figure3_Repeat_Stability')
 fig,ax=plt.subplots(figsize=(6.6,3.6),layout='constrained')
 for k,n in enumerate(['MRI','Fusion','MRI_eroded','Fusion_eroded']):
  m=main['metrics'][n];ci=main['patient_cluster_bootstrap_95ci'][n+'__roc_auc']
  ax.errorbar(m['roc_auc'],k,xerr=[[m['roc_auc']-ci['lower']],[ci['upper']-m['roc_auc']]],fmt='o',color=colors[n.removesuffix('_eroded')],capsize=3)
 ax.set_yticks(range(4),['MRI','Fusion','Eroded MRI','Eroded fusion']);ax.invert_yaxis();ax.set(xlim=(0,1),xlabel='OOF AUC with patient-bootstrap 95% interval',title='Boundary sensitivity on the same 182 scans');save(fig,'FigureS1_Boundary_Sensitivity')
 fig,axes=plt.subplots(1,2,figsize=(9.5,3.8),layout='constrained');ss=stable['single_scan']
 for k,n in enumerate(MODELS):
  m=ss['metrics'][n];ci=ss['bootstrap_95ci'][n+'__roc_auc']
  axes[0].errorbar(m['roc_auc'],k,xerr=[[m['roc_auc']-ci['lower']],[ci['upper']-m['roc_auc']]],fmt='o',color=colors[n],capsize=3)
  axes[1].bar(k,m['specificity_treatment_change'],color=colors[n]);axes[1].text(k,m['specificity_treatment_change']+.03,f'{m["tn"]}/22',ha='center')
 axes[0].set_yticks(range(4),MODELS);axes[0].invert_yaxis();axes[0].set(xlim=(0,1),xlabel='OOF AUC and patient-bootstrap 95% interval',title='A  One available scan per patient')
 axes[1].set_xticks(range(4),MODELS);axes[1].set(ylim=(0,1),ylabel='Treatment-change recall at tumor p < 0.5',title='B  Fixed threshold in 135 selected scans');save(fig,'FigureS2_Single_Scan')


def notebook(root=ROOT):
 md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
 cells=[md('# 第20步 表图与数值来源整理\n\n仅读取既有分析结果并计算描述性人群表，不拟合新模型、不做新检验、不起草论文正文。原第18步为主分析，全部敏感性结果保留。'),
 code("from pathlib import Path\nimport sys,json,hashlib,importlib.util\nimport pandas as pd\nROOT=Path.cwd()\nif not (ROOT/'src').exists(): ROOT=ROOT.parent\nspec=importlib.util.spec_from_file_location('paper_materials',ROOT/'scripts/make_ucsd_paper_materials.py')\nmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\npackage=module.generate(ROOT)\nprint('Tables / figures:',len(package['tables']),len(package['figures']))\nprint('Manuscript body drafted:',package['manuscript_body_drafted'])"),
 code("for table in package['tables']:\n    print(table['title'])\n    print(pd.DataFrame(table['rows'],columns=table['headers']).to_string(index=False))"),
 code("clinical=pd.read_csv(ROOT/'data/processed/ucsd_clinical_revalidated_cohort.csv')\nimage=pd.read_csv(ROOT/'data/processed/ucsd_clinical_image_features.csv')\nassert len(clinical)==238 and len(image)==182\nassert image.patient_id.nunique()==135\nprint('Class-specific unique patient counts:',image.groupby('tumor_label').patient_id.nunique().to_dict())\nprint('Overlap patients across labels:',len(set(image.loc[image.tumor_label.eq(0),'patient_id'])&set(image.loc[image.tumor_label.eq(1),'patient_id'])))\nprint('Baseline summaries use scan rows; no group p-values.')"),
 code("from IPython.display import display,Image\nfigdir=ROOT/'outputs/ucsd-paper-materials-20261029/figures'\ndisplay(Image(filename=str(figdir/'Figure1_Cohort_Flow.png'),width=650))\ndisplay(Image(filename=str(figdir/'Figure2_Main_Comparison.png'),width=1100))"),
 code("receipt=json.loads((ROOT/'reports/ucsd_paper_materials/generation_receipt.json').read_text())\nfor p,h in receipt['input_sha256'].items():\n    assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h\nassert receipt['model_refits']==0 and receipt['new_hypothesis_tests']==0\nprint('Frozen sources verified; manuscript writing awaits user instructions.')")]
 nbf.write(nbf.v4.new_notebook(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'))),root/'notebooks/20_ucsd_paper_tables_and_figures.ipynb')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--notebook-only',action='store_true');a=p.parse_args()
 if a.notebook_only:notebook()
 else:generate()
