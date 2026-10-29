from pathlib import Path
import sys
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
md,code=nbf.v4.new_markdown_cell,nbf.v4.new_code_cell
nb=nbf.v4.new_notebook(cells=[
 md('# 16 六例镜像扩展：统一ROI与强度处理技术试验\n\n用户已批准本阶段。固定6名不同源患者，3次治疗改变、3次肿瘤，仅作技术试验。协议`reports/ucsd_roi_pilot_protocol.md`；运行后因FLAIR裁切损失增加的工程修正单独记录于`reports/ucsd_roi_pilot_intensity_amendment.md`，不追写为预设方案。'),
 code("from pathlib import Path\nimport sys,json,runpy\nimport numpy as np\nimport pandas as pd\nfrom IPython.display import display,Image\nROOT=Path.cwd()\nif ROOT.name=='notebooks':ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.ucsd_roi_pilot import run,SAMPLE_IDS\ns=run(ROOT)\nbase=ROOT/'reports/ucsd_roi_pilot'\nprint(json.dumps(s,indent=2))\nassert s['source_files_available']==s['source_files_decoded']==36\nassert s['source_units_unknown']==36 and s['source_physical_QC_pass']==0"),
 md('## 同一源标注区域并集\n\n每例只合并普通BraTS所有正整数标签，保留全部连通区域，不按类别修改规则。不声称纯肿瘤组织或独立盲法。一次6邻域腐蚀仅为边界敏感性诊断，单位为体素。'),
 code("cases=pd.read_csv(base/'case_ROI_diagnostics.csv')\nqc=pd.read_csv(base/'source_file_QC.csv')\ndisplay(cases[['ID','tumor_label','roi_voxels','components_26','erosion_voxels','erosion_retention','success']])\nassert len(cases)==cases.patient_id.nunique()==6\nassert cases.tumor_label.value_counts().to_dict()=={0:3,1:3}\nassert cases.success.all() and cases.roi_nonempty.all()\nassert qc.relative_grid_status.eq('native_matrix_match').all()\nassert not cases.physical_volume_computed.any()"),
 md('## 初始裁切方案及执行后追加的不裁切修正\n\n预设按每图非零支持区p1/p99缩放并裁切，所有24份结构图均成功。但ROI上端裁切最高约26%，因此保留初始结果并追加同参数不裁切线性缩放。该工程选择不使用类别或模型效果，不能称预先注册或最优。32箱用于技术诊断，不报告分类显著性。'),
 code("from rn_public.ucsd_intensity_followup import run as followup\nchoice=followup(ROOT)\noriginal=pd.read_csv(base/'normalization_diagnostics.csv')\nrevised=pd.read_csv(base/'unclipped_normalization_diagnostics.csv')\ndisplay(original[['ID','sequence','clipped_high_fraction','erosion_JS_distance']])\ndisplay(revised[['ID','sequence','normalized_minimum','normalized_maximum','occupied_bins','erosion_JS_distance']])\nassert len(original)==len(revised)==24\nassert revised.success.all() and choice['added_after_observing_clipping']\nassert not choice['uses_clinical_class'] and not choice['model_performance_used']\nprint(json.dumps(choice,indent=2))"),
 md('## 实际源影像与派生ROI审阅图\n\n选取ROI最大横断面，仅用于技术显示，三维处理使用全部区域。蓝色为全部源标注并集、橙色为一次腐蚀；图像对比度仅作显示。两套直方图分别保留。'),
 code("runpy.run_path(str(ROOT/'scripts/plot_ucsd_roi_pilot.py'),run_name='__main__')\nfor name in ['six_case_ROI_review.png','six_case_intensity_histograms.png','six_case_unclipped_histograms.png']:\n    display(Image(filename=str(ROOT/'outputs/ucsd-roi-pilot-20261029'/name)))"),
 md('## 解释边界及下一阶段\n\n两组同规则技术处理成功，不等于独立临床验证。空间单位、原始定量ADC及源标注盲法仍未确认。下一阶段若获批，可按固定ROI和不裁切方案提取有限的探索性特征，并在共同病例上保留临床对照；本步没有模型或AUC。'),
 code("tests=json.loads((base/'software_test_receipt.json').read_text())\nprint(json.dumps(tests,indent=2))\nassert tests['success'] and tests['tests_run']==67\nassert not s['MRI_model_fitted'] and not s['MRI_performance_estimated']\nassert not s['clinical_model_refitted'] and not s['whole_cohort_downloaded']\nassert s['next_step_requires_user_approval']\nprint('Six-case technical pilot complete. Await next-stage approval.')")
])
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
nbf.write(nb,ROOT/'notebooks/16_ucsd_roi_and_intensity_pilot.ipynb')
print('Created Notebook16')
