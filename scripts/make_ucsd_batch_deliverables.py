"""Stage17 descriptive outputs and Notebook; no fitting or outcome-based selection."""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
import nbformat as nbf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_batch_features import FEATURES


def generate(root=ROOT, notebook=True):
 root=Path(root);out=root/'reports/ucsd_batch_features';fig=root/'figures/ucsd_batch_features';fig.mkdir(parents=True,exist_ok=True)
 primary=pd.read_csv(root/'data/processed/ucsd_image_features.csv')
 eroded=pd.read_csv(root/'data/processed/ucsd_image_features_eroded.csv')
 joined=pd.read_csv(root/'data/processed/ucsd_clinical_image_features.csv')
 cases=pd.read_csv(out/'all_clinical_case_status.csv');files=pd.read_csv(out/'actual_file_QC.csv')
 diagnostics=pd.read_csv(out/'normalization_and_texture_diagnostics.csv')
 summary=json.loads((out/'batch_receipt.json').read_text())['summary']
 definitions=[]
 for seq in ['FLAIR','T1post']:
  for suffix,meaning,unit in [
   ('mean','ROI内不裁切p1/p99线性缩放后的均值','dimensionless'),
   ('std','同上，群体标准差，ddof=0','dimensionless'),
   ('entropy','原ROI最小/最大固定32箱，Shannon熵，log2','bits'),
   ('glcm_contrast','13个无向原生网格相邻方向，对称计数合并后归一化，Σ(i−j)²pij','bin_index_squared')]:
   definitions.append(dict(feature=seq+'_'+suffix,sequence=seq,definition=meaning,units=unit,
    ROI='ordinary_BraTS_positive_label_union',normalization='per_image_nonzero_finite_p1_p99_affine_no_clipping',
    sensitivity='one_6_neighbour_voxel_erosion_same_normalization_and_base_ROI_bin_bounds',
    allowed_model_predictor=True,physical_distance_assumed=False))
 definitions=pd.DataFrame(definitions);definitions.to_csv(out/'feature_dictionary.csv',index=False)
 a=primary.set_index('ID')[list(FEATURES)];b=eroded.set_index('ID')[list(FEATURES)].reindex(a.index)
 rows=[]
 for feature in FEATURES:
  delta=b[feature]-a[feature];rel=delta.abs()/a[feature].abs().replace(0,np.nan)
  rows.append(dict(feature=feature,n_primary=int(a[feature].notna().sum()),primary_min=float(a[feature].min()),
   primary_q25=float(a[feature].quantile(.25)),primary_median=float(a[feature].median()),
   primary_q75=float(a[feature].quantile(.75)),primary_max=float(a[feature].max()),
   n_eroded=int(b[feature].notna().sum()),median_signed_delta=float(delta.median()),
   median_absolute_delta=float(delta.abs().median()),max_absolute_delta=float(delta.abs().max()),
   n_relative_nonzero_denominator=int(rel.notna().sum()),median_absolute_relative_delta=float(rel.median()),
   max_absolute_relative_delta=float(rel.max())))
 stats=pd.DataFrame(rows);stats.to_csv(out/'feature_descriptive_summary.csv',index=False)
 coverage=cases.groupby(['status','tumor_label'],dropna=False).agg(scans=('ID','size'),source_patients=('patient_id','nunique')).reset_index()
 coverage.to_csv(out/'coverage_by_status_and_label.csv',index=False)
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
 fig1,ax=plt.subplots(figsize=(7.4,3.8))
 vals=[len(cases),summary['target_timepoints'],len(primary),summary['eroded_complete_timepoints']]
 ax.barh(['Revalidated clinical','Listed three-file MRI set','Complete eight features','Complete eroded features'],vals,color=['#8C9BA8','#5A7E9B','#35556D','#879D7E'])
 for i,v in enumerate(vals):ax.text(v+2,i,str(v),va='center')
 ax.set_xlim(0,max(vals)*1.13);ax.invert_yaxis();ax.set_xlabel('Scan timepoints (repeated patients included)');fig1.tight_layout()
 def save_figure(figure,name):
  for ext in ['png','pdf']:
   destination=fig/(name+'.'+ext);part=destination.with_name(destination.name+'.partial')
   figure.savefig(part,format=ext,dpi=170);part.replace(destination)
 save_figure(fig1,'coverage')
 plt.close(fig1)
 fig2,axes=plt.subplots(2,4,figsize=(12,6))
 for ax,feature in zip(axes.flat,FEATURES):
  delta=b[feature]-a[feature]
  ax.hist(delta.dropna(),bins=20,color='#5A7E9B',edgecolor='white',linewidth=.5)
  ax.axvline(0,color='#9B573A',lw=1);ax.set_title(feature,fontsize=10);ax.set_xlabel('Eroded minus original');ax.set_ylabel('Scan timepoints')
  ax.xaxis.set_major_locator(MaxNLocator(4))
 fig2.suptitle('One-voxel boundary sensitivity with frozen normalization and bins',fontsize=12)
 fig2.tight_layout(rect=(0,0,1,.95))
 save_figure(fig2,'boundary_deltas')
 plt.close(fig2)
 def dataset(df):return dict(headers=list(df.columns),rows=json.loads(df.to_json(orient='values',force_ascii=False)))
 payload=dict(summary=summary,datasets={
  'Features':dataset(joined[['ID','patient_id','validation_group','tumor_label',*FEATURES,*[x for x in joined if x not in ['ID','patient_id','validation_group','tumor_label',*FEATURES]]]]),
  'Sensitivity':dataset(eroded),'Cases':dataset(cases[['ID','patient_id','tumor_label','status','error','eroded_complete','erosion_retention',*[x for x in cases if x not in ['ID','patient_id','tumor_label','status','error','eroded_complete','erosion_retention']]]]),
  'Files':dataset(files[['ID','sequence','decoded','digest_matches','gzip_crc_verified','relative_grid_match','spatial_units','bytes',*[x for x in files if x not in ['ID','sequence','decoded','digest_matches','gzip_crc_verified','relative_grid_match','spatial_units','bytes']]]]),
  'Definitions':dataset(definitions),'Diagnostics':dataset(diagnostics),'Distributions':dataset(stats)},
  source_note='UCSD-PTGBM DOI 10.7937/fwv2-dt74; public mirror https://github.com/data-nih/tcia/releases; source_manifest.csv pins file URLs and SHA256. Clinical join: frozen Stage13 UCSD cohort; original workbooks retained.')
 (root/'reports/ucsd_batch_workbook_input.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False))
 if notebook:write_notebook(root)
 return stats


def write_notebook(root):
 md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
 cells=[md('# 第17步：批量有限影像特征与临床连接\n\n182次目标扫描；只提取预先固定8项特征，不拟合模型或计算AUC。普通BraTS全部正标签并集称为源标注区域，标注盲法未确认。空间单位unknown，不推定mm或mL；uint8图像只能研究此公开派生版本。'),
 code("from pathlib import Path\nimport sys,json\nimport numpy as np,pandas as pd\nROOT=Path.cwd()\nif not (ROOT/'src').exists(): ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.ucsd_batch_features import run,FEATURES\nsummary=run(ROOT,download=False,workers=4)\nprint(json.dumps(summary,indent=2,ensure_ascii=False))"),
 md('源文件必须先恢复或下载。成功检查点绑定处理代码、协议和输入SHA256，再次使用前仍核对实际源文件。源文件缺失时不把已保存的特征缓存误认为本次提取成功。'),
 code("out=ROOT/'reports/ucsd_batch_features'\ncases=pd.read_csv(out/'all_clinical_case_status.csv')\nfiles=pd.read_csv(out/'actual_file_QC.csv')\nprint(cases.groupby(['status','tumor_label']).agg(scans=('ID','size'),patients=('patient_id','nunique')))\nassert len(cases)==238 and len(files)==546\nprint('Actual decoded files:',int(files.decoded.sum()))\nprint('Spatial units:',files.spatial_units.value_counts().to_dict())\nprint('Processing failures:',cases.loc[cases.status.eq('processing_failed'),['ID','error']].to_dict('records'))"),
 code("primary=pd.read_csv(ROOT/'data/processed/ucsd_image_features.csv')\njoined=pd.read_csv(ROOT/'data/processed/ucsd_clinical_image_features.csv')\nassert list(primary.columns)==['ID',*FEATURES]\nassert np.isfinite(primary[list(FEATURES)].to_numpy()).all()\nassert primary.ID.is_unique and joined.ID.is_unique\nassert set(primary.ID)==set(joined.ID)\nprint('Joined scans / source patients / validation groups:',len(joined),joined.patient_id.nunique(),joined.validation_group.nunique())\nprint('Clinical interval missing:',int(joined.initial_event_missing.sum()))\nprint('Labels (1=tumor, 0=treatment change):',joined.tumor_label.value_counts().to_dict())\nprint('Fixed MRI predictors:',list(FEATURES))"),
 md('一次6邻域腐蚀仅作边界敏感性分析。保持每图归一化参数与原ROI离散边界不变。下列分布不按类别筛选特征，不作显著性检验；重复扫描不是独立患者样本。'),
 code("import importlib.util\nspec=importlib.util.spec_from_file_location('batch_deliverables',ROOT/'scripts/make_ucsd_batch_deliverables.py')\nmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\nstats=module.generate(ROOT,notebook=False)\nprint(stats[['feature','n_primary','n_eroded','median_absolute_relative_delta','max_absolute_relative_delta']].to_string(index=False))\nfrom IPython.display import display,Image\ndisplay(Image(filename=str(ROOT/'figures/ucsd_batch_features/coverage.png')))\ndisplay(Image(filename=str(ROOT/'figures/ucsd_batch_features/boundary_deltas.png')))"),
 code("import hashlib\nreceipt=json.loads((out/'batch_receipt.json').read_text())\nfor p,expected in receipt['summary']['protocol_and_code_sha256'].items():\n    assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected\nassert not summary['MRI_model_fitted'] and not summary['classification_metrics_computed']\nprint('Protocol and code fingerprints verified. No MRI model fitted.')\nprint('Next proposed stage: same-case clinical controls and limited penalized MRI fusion with patient-grouped validation, only after approval.')"),
 md('下一步必须在共同影像病例上重建患者分组验证，临床对照也在相同病例/折重新估计。归一化之外的填补、标准化和任何特征处理只在训练折学习。不能把该子队列的新AUC与第13步238次扫描的旧AUC直接当作增益。')]
 nb=nbf.v4.new_notebook(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')))
 nbf.write(nb,root/'notebooks/17_ucsd_batch_image_features.ipynb')


if __name__=='__main__':print(generate().to_string(index=False))
