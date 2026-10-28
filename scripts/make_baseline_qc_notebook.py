"""Build the current-cohort complete mask-series QC notebook."""
from pathlib import Path
import sys
import nbformat as nbf

root=Path(__file__).resolve().parents[1]
md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
nb=nbf.v4.new_notebook(cells=[
 md('# 07 基线分割对应MRI全序列核查\n\n范围是当前54个病灶基线候选、41名患者、48组检查的掩膜对应序列，共6,936张DICOM；不是全部42,385张影像，也不包含本轮未恢复的全部FLAIR序列。先运行`restore_sources.py`，恢复已有MRI分卷后运行`restore_baseline_mask_series.py`。也可通过其`--download-missing`参数从原始公开Figshare恢复所需成员。'),
 code("from pathlib import Path\nimport sys,json,runpy,gzip,hashlib\nimport pandas as pd\nROOT=Path.cwd()\nif ROOT.name=='notebooks':ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nmanifest=ROOT/'data/metadata/baseline_qc/mask_series_members.jsonl.gz'\nraw=gzip.decompress(manifest.read_bytes())\nentries=[json.loads(x) for x in raw.decode().splitlines()]\nassert len(entries)==6936\nassert len({x['member'] for x in entries})==6936\nprint('Input manifest SHA256:',hashlib.sha256(raw).hexdigest())"),
 md('## 逐文件及逐序列检查\n\n像素解码、SHA256、CRC32和头信息检查覆盖全部所选切片。按空间位置排序，以首末切片位置差除以间隔数构造多切片仿射，并对所有中间层检查残差；这避免相邻位移中位数的舍入误差累计。相邻层间距中位数仍用于报告和不规则间距诊断。工程容差保持不变，不代表临床阈值。'),
 code("run=runpy.run_path(str(ROOT/'scripts/audit_additional_imaging.py'))['run']\nsummary=run(manifest_relative='data/metadata/baseline_qc/mask_series_members.jsonl',prefix='cohort',output_subdir='baseline-qc-20261028',scope='complete MRI series named by 54 baseline mask candidates; not all modalities',mask_candidates_only=True,write_overlays=False)\nf=pd.read_csv(ROOT/'data/processed/cohort_dicom_file_qc.csv.gz')\ns=pd.read_csv(ROOT/'data/processed/cohort_dicom_series_qc.csv')\nassert len(f)==s.files.sum()==6936\nassert f.sha256_match.sum()==f.crc32_match.sum()==6936\nprint(s[['patient_id','study_date_code','series_name','files','constant_slices','spacing_tag_position_mismatch','technical_stack_pass']].to_string(index=False))"),
 md('## 名称对应与网格误差\n\n先保留精确名称匹配；只允许唯一的标点/大小写变体对应，歧义时停止，不进行模糊匹配。原掩膜与DICOM名称均保留，最终由空间坐标独立验证。全体积角点误差≤0.001体素且为完整有符号轴置换时才记录网格等价。超阈值记录不通过放宽容差、修改掩膜或插值转为通过。'),
 code("m=pd.read_csv(ROOT/'data/processed/cohort_baseline_mask_alignment.csv')\nassert len(m)==m.lesion_key.nunique()==54\nprint('Name mapping:',m.name_match_rule.value_counts().to_dict())\nprint('Alignment:',m.alignment_status.value_counts().to_dict())\nprint(m.loc[m.grid_equivalent==0,['lesion_key','max_corner_error_voxels','max_corner_error_mm','target_max_reindex_error_mm','alignment_status']].to_string(index=False))\nassert m.anatomical_review_complete.sum()==m.use_for_model.sum()==0"),
 md('## 常量切片与目标体素\n\n常量切片单独列为需要检查的项目，规则几何通过不等于图像质量通过。分割体素在连续DICOM坐标中的视野覆盖、以及最近层索引是否落在常量切片上，仅作为诊断性检查，不重采样或修改原标签。'),
 code("print(f.loc[f.constant_pixel_array==1,['patient_id','study_date_code','InstanceNumber','pixel_min','pixel_max']].to_string(index=False))\nprint('Target voxels on constant slices:',m.target_voxels_on_constant_slices.sum())\nprint('All target voxels inside image FOV:',bool(m.target_voxels_inside_image_fov.eq(m.target_voxels).all()))\nprint('Full cohort clinical image review:',summary['clinical_image_review_complete'])"),
 md('## 研究状态\n\n本轮不实施跨序列配准、不重画分割，也不把几何通过转换成临床终点通过。下一步调查仍超出网格容差的病灶，恢复和核实对应FLAIR，再建立配准方案。影像合格不能弥补125条未知结局和缺少已核实阴性对照的问题。\n\n方法：[NiBabel多切片仿射](https://nipy.org/nibabel/dicom/dicom_orientation.html#getting-a-3d-affine-from-a-dicom-slice-or-list-of-slices)、[DICOM图像平面](https://dicom.nema.org/medical/dicom/2026c/output/chtml/part03/sect_C.7.6.2.html)。'),
 code("c=pd.read_csv(ROOT/'data/processed/clinical_current.csv')\nassert c.rn_time_day.isna().sum()==125\nassert c.verified_non_event.sum()==0\nassert summary['models_fitted'] is False\nprint('RN unknown: 125; verified non-events: 0; no model fitted.')")
])
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
nbf.write(nb,root/'notebooks/07_baseline_mask_series_qc.ipynb')
print('Created Notebook 07')
