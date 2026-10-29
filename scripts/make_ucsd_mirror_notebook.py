"""Create the actual two-case mirror download/QC notebook."""
from pathlib import Path
import sys
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb = nbf.v4.new_notebook(cells=[
    md('# 15 普通HTTPS镜像：两例真实MRI下载与技术验证\n\n用户已批准替代路线，不以官方原始来源认证为前提。0002_01与0005_01按固定清单下载12文件，原始文件名与内容不改写。见`reports/ucsd_mri_mirror_sample_plan.md`。这两例仅供技术验证，不估计诊断性能。'),
    code("from pathlib import Path\nimport sys,json,runpy,hashlib\nimport numpy as np\nimport pandas as pd\nfrom IPython.display import display,Image\nROOT=Path.cwd()\nif ROOT.name=='notebooks':ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.ucsd_mri_mirror import run,SAMPLE_IDS\ns=run(ROOT)\nprint(json.dumps(s,indent=2))\nassert s['successful_download_files']==s['decoded_image_files']==12\nassert s['sample_two_ID_bindings_match'] is True"),
    md('## 临床连接及目录覆盖\n\n镜像清单不是下载结果。184个FLAIR目录中，隔离已知ID冲突后，有182个时间点可与现有临床表连接；当前只取得两例12文件。病例通过显式镜像ID与BraTS ID核对，标签仍沿用第13步源表。'),
    code("base=ROOT/'reports/ucsd_mri_mirror'\ncoverage=pd.read_csv(base/'clinical_mirror_sequence_coverage.csv')\nmapping=pd.read_csv(base/'sample_case_mapping.csv')\ndisplay(mapping)\ndisplay(coverage.groupby(['listed_all_six','tumor_label']).agg(timepoints=('ID','size'),source_patients=('patient_id','nunique')))\nassert len(coverage)==238 and coverage.patient_id.nunique()==176\nassert coverage.actual_download_complete.sum()==2\nassert set(mapping.ID)==set(SAMPLE_IDS)"),
    md('## 完整体素与两种网格检查\n\n12份文件均可解码，但空间单位unknown，预设物理尺度检查仍未通过。所有强度序列为uint8、slope=1、intercept=0，值域0–255；不把ADC解释成原始物理量。新增无单位的原生仿射比较只用于同体素索引叠加，不赋予毫米或临床配准通过。'),
    code("qc=pd.read_csv(base/'sample_file_qc.csv')\ndisplay(qc[['ID','sequence','shape','stored_dtype','spatial_units','minimum','maximum','decoded','relative_grid_status','technical_pass','issues']])\nreceipt=json.loads((base/'sample_qc_receipt.json').read_text())\nassert all(r['gzip_crc_verified'] and r['release_digest_matches'] for r in receipt['files'])\nassert s['unknown_spatial_unit_files']==12\nassert s['relative_native_grid_matches']==12\nassert s['technical_pass_image_files']==0\nassert all(r['nonfinite_voxels']==0 for r in receipt['files'])"),
    md('## 真实图像预览\n\n下图来自实际镜像文件，非测试数组。切片按FLAIR非零包围盒中点固定选择，不按临床类别或分割大小挑图。仅为头部方向下的技术预览，原文件不写回、不注册；分割颜色只表示观察到的整数值。'),
    code("runpy.run_path(str(ROOT/'scripts/plot_ucsd_mirror_samples.py'),run_name='__main__')\nfor name in ['actual_FLAIR_planes.png','actual_multisequence_axial.png','actual_segmentation_overlay.png']:\n    display(Image(filename=str(ROOT/'outputs/ucsd-mri-mirror-20261029'/name)))"),
    md('## 本步结果与限制\n\n下载和解码路线已打通，用户无需手动下载；物理尺度、定量强度和统一预测ROI仍有待解决。未下载细胞性参考分割，未提取预测特征，未训练MRI模型，也未重训临床模型。下一研究阶段按用户要求等待批准。'),
    code("tests=json.loads((base/'software_test_receipt.json').read_text())\nprint(json.dumps(tests,indent=2))\nassert tests['success']\nassert not s['MRI_model_fitted'] and not s['clinical_models_refitted']\nassert not s['prediction_features_extracted'] and not s['ROI_for_prediction_approved']\nassert s['code_sha256']==hashlib.sha256((ROOT/'src/rn_public/ucsd_mri_mirror.py').read_bytes()).hexdigest()\nprint('Actual sample acquisition/decoding completed. Physical-scale acceptance and prediction ROI remain incomplete.')")
])
nb.metadata = {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
               'language_info': {'name': 'python', 'version': sys.version.split()[0]}}
nbf.write(nb, ROOT/'notebooks/15_ucsd_mri_mirror_samples.ipynb')
print('Created Notebook15')
