# 新增基线MRI逐文件技术质控

完成日期：2026-10-28。只使用既有公开去标识数据。本轮范围为临床版本更新后补充的4组患者—日期检查；未把原先40,801张影像的首尾抽样升级为全量质控。

## 已完成的检查

| 项目 | 结果 |
| --- | ---: |
| 检查 / DICOM / 序列目录 | 4 / 1,584 / 28 |
| 文件大小、CRC32、SHA256全部匹配 | 1,584 |
| 像素可读取、形状与头信息一致 | 1,584 |
| 非有限像素 / 常量切片 / 重复SOP UID / 日期不一致 | 0 / 0 / 0 / 0 |
| 可构成规则单帧影像堆栈的序列 | 28 |
| 层间距标签与实际位置不一致 | 3 |
| T2-FLAIR名称候选 / T1-FLAIR另列 | 4 / 3 |
| 投影或重建序列另列 | 8 |
| 对应基线病灶候选 / 同期公开掩膜 | 7 / 1 |

4组检查为20001/19000810、20013/19000130、20020/19000216及40093/19010113；日期均为去标识编码。前3组共1,254张来自DICOMs_2.zip，最后一组330张来自DICOMs_4.zip。校验对象为此前已验证并保存的追加下载清单，逐文件记录源成员、哈希、CRC结果、像素范围及空间字段。

## 空间信息与序列选择

按SeriesInstanceUID分组，以ImagePositionPatient在ImageOrientationPatient法向上的投影排序。不使用文件名、InstanceNumber或SliceThickness推导切片顺序和间距。列索引、行索引分别对应PixelSpacing的第二、第一分量；仿射由LPS转为RAS，并保留逐层的平面内位移。只有位置、方向、间距及矩阵一致的单帧规则堆栈才获得技术通过标记。这个标记不判定运动伪影、覆盖范围是否充分或病灶诊断。

40093的3个序列存在层间距标签差异：

| 序列 | 位置计算间距（mm） | SpacingBetweenSlices（mm） |
| --- | ---: | ---: |
| AX_T1_FL3D | 1.250000 | 1.0 |
| CORONALES_C | 2.000000 | 1.0 |
| SAGITALES_C | 2.011407 | 1.0 |

4个T2-FLAIR候选的相邻层中心距均大于SliceThickness。前三组为4.4/4.0 mm，40093为6.5/5.0 mm；这是规则采集层间隙，不按缺失文件处理，也不意味着适合未经评估的体素级融合。20020的名称含GADO，后续须明确是否与预设的对比剂前/后FLAIR口径一致。T1-FLAIR名称的3个序列不作为T2-FLAIR使用。投影/重建序列不当作独立原始采集。所有1,584张的ContrastBolusAgent字段均为空；名称提示、影像外观及现有分割均不能提供给药时间证据。

## 40093_L3分割匹配

原始掩膜SHA256与既有373份掩膜核查清单一致。分割512×512×120与AX_T1_FL3D在两轴翻转后网格等价：

`image_column=511-mask_x; image_row=511-mask_y; image_slice=mask_z`

完整体积8个角点的最大误差约0.000114934体素，低于本轮工程容差0.001体素。397个目标体素全部落在影像内。未实施插值、跨序列配准或标签重画。保存了目标出现范围内3张切片的[轮廓叠加图](../outputs/imaging-qc-20261028/40093_L3_mask_overlay.png)；可见轮廓围绕局部高信号区域，此项技术观察不构成RN诊断或临床分割质量认证。其余6个病灶候选缺少对应基线公开掩膜，不使用后续时间点分割代替。

## 重现与验证

```bash
python -m pip install -r requirements.txt
python scripts/restore_sources.py
# 已恢复追加影像时可跳过下载；支持追加包中的data/imaging/dicom路径。
python scripts/download_current_baselines.py
python scripts/run_notebooks_kernel.py notebooks/05_endpoint_versions_and_followup.ipynb notebooks/06_additional_baseline_imaging_qc.ipynb
python scripts/make_imaging_qc_workbook_input.py
python -m unittest discover -s tests -v
```

Excel由`build_imaging_qc_workbook.mjs`使用artifact-tool生成，含Summary、Series、Lesions、Files四页。目录中的逐文件CSV保留完整空间元数据，Excel保留便于审阅的字段及全部1,584行。汇总使用公式，并核对缓存结果；已渲染检查四页布局。Excel生成需已提供artifact-tool的Node环境，Python命令本身不生成Excel。

05、06均通过进程内ipykernel执行，每份5个代码单元、0个错误，回执见`kernel_execution.json`。独立内核服务器和浏览器前端仍未验证。25项测试通过，新增6项覆盖行列坐标、方向变化、重复平面、不规则缺层、轴翻转、累积网格漂移及T1/T2-FLAIR区分。工程容差及输入文件SHA256见`additional_imaging_qc.json`，不把工程阈值解释为临床阈值。

## 下一步与当前研究状态

将同一套逐文件检查扩展到原归档基线序列，优先核验54个有实际基线掩膜的候选，再确定T1增强与T2-FLAIR的序列和配准方案。原归档仍需恢复对应影像后才能逐文件检查，已有938张首尾抽样不能代替全序列。运动、病灶定位和临床可用性仍需专门审阅，新增4组检查也没有被标记为完成临床图像质量判定。

当前仍为75名患者、160个病灶、35个数值型RN时间、125个未知、0个已核实阴性；基线掩膜候选54个、41名患者、18个RN时间。未填补标签、未拟合模型、未计算AUC。全量临床终点核实及正式预测期限仍待确定，不能把本轮技术进展当作建模条件已满足。

方法来源：[DICOM Image Plane Module](https://dicom.nema.org/medical/dicom/2026c/output/chtml/part03/sect_C.7.6.2.html)、[NiBabel DICOM orientation](https://nipy.org/nibabel/dicom/dicom_orientation.html)、[NiBabel坐标系统](https://nipy.org/nibabel/coordinate_systems.html)、[pydicom像素处理](https://pydicom.github.io/pydicom/stable/guides/user/working_with_pixel_data.html)。原始来源：[MOLAB](https://molab.es/datasets-brain-metastasis-1/)、[DICOMs_2](https://figshare.com/articles/dataset/22271017)、[DICOMs_4](https://figshare.com/articles/dataset/22271233)。
