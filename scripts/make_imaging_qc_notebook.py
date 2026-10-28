"""Build Notebook 06 for all-file technical QC of four added baseline studies."""
from pathlib import Path
import sys
import nbformat as nbf

root=Path(__file__).resolve().parents[1]
md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
nb=nbf.v4.new_notebook(cells=[
 md('# 06 新增基线MRI逐文件技术质控\n\n范围限定于临床版本更新后追加的4组基线检查、1,584个DICOM。需要恢复追加包或运行下载脚本；不把其余40,801个已归档文件描述为完成本轮检查。空白RN不变为阴性，技术通过不等于病灶诊断或临床图像质量通过。'),
 code("from pathlib import Path\nimport sys,json,runpy\nimport pandas as pd\nROOT=Path.cwd()\nif ROOT.name=='notebooks':ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nsummary=runpy.run_path(str(ROOT/'scripts/audit_additional_imaging.py'))['run']()\nassert summary['dicom_files']==1584\nassert summary['integrity_verified_files']==summary['pixel_decodable_files']==1584"),
 md('## 序列与空间坐标\n\n按SeriesInstanceUID分组。使用ImagePositionPatient在切片法向的投影排序，不使用文件名或InstanceNumber；仿射保留平面内位移。DICOM的LPS坐标转为NIfTI使用的RAS坐标。工程容差见报告，不代表临床可接受阈值。常规序列中的层间隙与不规则缺层分别报告。'),
 code("s=pd.read_csv(ROOT/'data/processed/additional_dicom_series_qc.csv')\nprint(s[['patient_id','series_name','files','slice_step_mm','technical_stack_pass','spacing_tag_position_mismatch','t2_flair_metadata_candidate','derived_or_projection_hint']].to_string(index=False))\nassert s.files.sum()==1584\nprint('Spacing tag discrepancies:',summary['spacing_tag_position_mismatch_groups'])\nprint('T2-FLAIR candidates with slice gaps:',summary['t2_flair_candidates_with_interslice_gap'])"),
 md('## 分割与影像网格匹配\n\n追加检查对应7个病灶基线候选，只有40093_L3有同期公开掩膜。比较完整体积8个角点在影像网格中的映射，仅当其为有符号轴置换且误差≤0.001体素时认可网格等价。这里不做插值或配准。397个目标体素来自既有分割，不是RN诊断标签。'),
 code("m=pd.read_csv(ROOT/'data/processed/additional_baseline_mask_alignment.csv')\nprint(m[['lesion_key','study_date_code','baseline_mask_available','alignment_status','max_corner_error_voxels','target_voxels_inside_image']].to_string(index=False))\nx=m[m.grid_equivalent==1]\nassert len(x)==1\nassert x.iloc[0].target_voxels_inside_image==397\nassert m.use_for_model.sum()==0"),
 md('## 分割轮廓叠加图\n\n图中轮廓使用同一网格的整数索引翻转，未修改原始MRI或掩膜。图像展示用于技术复核，不构成RN诊断或正式临床质量判定。'),
 code("from IPython.display import Image,display\ndisplay(Image(filename=str(ROOT/'outputs/imaging-qc-20261028/40093_L3_mask_overlay.png')))"),
 md('## 解释与后续\n\n4组检查均有T2-FLAIR名称候选；3个T1-FLAIR不混用；8个投影/重建序列单独标识，不作为独立原始采集。所有文件的ContrastBolusAgent均未填写，序列名称和本图显示的信号不能确定注射时间。T1与T2-FLAIR配准仍未实施。下一步扩展原归档基线序列的逐文件质控，同时继续核实公开结局证据；125条未知结局及0条已核实阴性保持不变。\n\n方法依据：[DICOM Image Plane Module](https://dicom.nema.org/medical/dicom/2026c/output/chtml/part03/sect_C.7.6.2.html)、[NiBabel DICOM orientation](https://nipy.org/nibabel/dicom/dicom_orientation.html)、[NiBabel coordinate systems](https://nipy.org/nibabel/coordinate_systems.html)、[pydicom pixel data](https://pydicom.github.io/pydicom/stable/guides/user/working_with_pixel_data.html)。'),
 code("c=pd.read_csv(ROOT/'data/processed/clinical_current.csv')\nassert c.rn_time_day.isna().sum()==125\nassert c.verified_non_event.sum()==0\nassert summary['models_fitted'] is False\nassert summary['full_selected_mri_qc_complete'] is False\nprint('Technical audit complete for added studies; full cohort image QC and endpoint adjudication remain pending.')")
])
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
nbf.write(nb,root/'notebooks/06_additional_baseline_imaging_qc.ipynb')
print('Created Notebook 06')
