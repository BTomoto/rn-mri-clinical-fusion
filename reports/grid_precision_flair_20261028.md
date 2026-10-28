# 坐标差异复核与FLAIR配对

日期：2026-10-28。仅分析既有公开去标识数据。本轮恢复48组基线掩膜检查中名称包含FLAIR且不包含T1的序列；不把名称筛选、相同空间UID或坐标视野覆盖作为解剖配准通过。

## FLAIR恢复与技术检查

| 项目 | 结果 |
| --- | ---: |
| 基线检查总数 | 48 |
| 有FLAIR名称候选的检查 / 序列 | 40 / 40 |
| 恢复并检查的FLAIR切片 | 1,391 |
| 解压字节数 | 478,581,234 |
| 大小、CRC32、SHA256及像素读取通过 | 1,391 |
| 几何规则、头信息日期匹配的序列 | 40 |
| 非有限像素 / 常量切片 / 重复SOP UID | 0 / 0 / 0 |
| 有采集层间隙的序列 | 38 |
| 有FLAIR候选的病灶 / 未找到的病灶 | 46 / 8 |

所需文件来自已保存的原16个MRI分卷及追加包内容，没有重新生成或替换源影像。16个分卷的SHA256均复核；每张FLAIR与先前下载清单的SHA256一致。成员清单gzip解压内容的SHA256为`b078376f9c79cba263897587acf60ecf26e97d86fcb6a2b42500033e6c307190`。逐文件数据与清单无损压缩保存，pandas可直接读取。

未找到FLAIR名称候选的8个病灶为10046_L1、40007_L1、40037_L1、40038_L1、40065_L1、40073_L1、40086_L1、40173_L1。该判断限于本项目所选Figshare基线日期目录，不宣称所有外部公开版本均无FLAIR，也不使用T1重建序列替代。

38个序列的中心间距大于SliceThickness，另2个3D_Brain_VIEW_FLAIR_Tra序列中心间距约0.6 mm、SliceThickness为1.2 mm；未把规则层间隙当作下载缺片。该厚层/重叠重建差异需要进入后续影像组学方案，不直接混作相同采集条件。全部切片ContrastBolusAgent为空，给药状态和时间未核实。

## 配对与40158_L1视野边界

46个病灶的T1对应序列与FLAIR具有相同的单一StudyInstanceUID及FrameOfReferenceUID。相同UID仅支持头信息关联，仍可能存在序列间头动和解剖错位。将原掩膜体素中心按其sform映射到FLAIR连续坐标，45个病灶全部处于其坐标范围内，1个为部分覆盖。

40158_L1共有8,706个目标体素中心，其中8,558个（98.30%）在FLAIR坐标范围内，148个超出切片轴下界。FLAIR形状为512×512×20；目标切片坐标范围约-0.658至1.557，行列方向未发现范围外体素。此项是坐标边界诊断，尚不能确定实际解剖缺失范围；切片中心间距约6.5 mm且厚度5 mm，也不能由坐标视野比例推断连续组织均被采集。

保存[原始切片技术审阅图](../outputs/flair-grid-qc-20261028/40158_L1_native_fov_review.png)，分别显示一张目标中心附近的T1原始切片、FLAIR第0和1层。十字为头信息投影的目标中心，不是新分割轮廓。显示前验证各切片SHA256；未重采样影像、配准或修改掩膜。该图不构成RN诊断或临床质量认证。

## 12个坐标差异病灶复核

12个病灶对应10个不同掩膜文件。逐一保留原qform、sform代码，比较两种仿射与DICOM的全体积角点偏差、首末平面偏差及层间步长。

- qform与sform之间最大角点差异约0.013296 mm；原sform与DICOM之间最大角点差异仍约0.104119 mm。
- 9个病灶的末平面较接近DICOM，3个的首平面较接近。
- NIfTI层间步长与DICOM首对或末对相邻切片步长之差均小于约0.0000065 mm。端点锚定与局部间距估计是与数值模式一致的解释，但缺少转换流程证据，不能据此确定具体成因或软件。
- 对20034_L1、20034_L2，单独采用qform时可满足既有0.001体素网格容差；其余10个在本次qform检查中仍未通过。

NiBabel在存在有效sform时按其默认规则选用sform；qform与sform可表示不同空间变换。上述2个结果仅作为敏感性诊断，没有按病例选择更容易通过的仿射。当前统一使用sform，严格网格匹配仍为42个、待复核12个，解决数量为0。该敏感性结果只来自12个待复核病例，没有据此推导全部54个病灶采用qform时的通过数。

未修改任何源头信息、标签、纳入状态或工程容差。亚体素差异既不自动视作分割错误，也没有未经依据就认定为临床可接受。

## 文件与重现

- `notebooks/08_grid_precision_and_flair_pairs.ipynb`：本轮分析、坐标诊断和原始切片技术审阅图。
- `data/processed/grid_precision_review.csv`：12条坐标复核记录。
- `data/processed/baseline_flair_pairs.csv`：54个病灶的配对候选、缺失及坐标视野结果。
- `data/processed/flair_dicom_series_qc.csv`与`flair_dicom_file_qc.csv.gz`：40个序列、1,391张切片。
- `outputs/flair-grid-qc-20261028/RN_FLAIR_Grid_Review.xlsx`：Summary、Pairs、GridReview、FLAIRSeries、Files五页，含全部切片记录与公式汇总；已渲染并核对缓存值。

```bash
python scripts/restore_sources.py
# 需要原始基线T1与FLAIR；已有分卷可放在dist/restored_mri下。
python scripts/restore_baseline_mask_series.py --download-missing
python scripts/restore_baseline_flair.py --download-missing
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_08.json notebooks/08_grid_precision_and_flair_pairs.ipynb
python scripts/make_flair_grid_workbook_input.py
python -m unittest discover -s tests -v
```

本轮Notebook08的5个代码单元通过进程内ipykernel执行，回执独立保存，未覆盖原05—07回执。29项测试通过，新增测试核对全体积累计误差的物理单位、世界坐标视野映射及半开边界。尚未验证独立内核服务器或浏览器前端。Excel由artifact-tool Node构建器生成，Python输入脚本本身不直接生成工作簿。

## 下一步与研究可行性

优先审阅40158_L1视野边界，针对其余配对设计少量刚性配准试验及质量判据；12个网格差异需继续保留统一处理规则。然后应回到公开临床终点核查，明确原计划风险模型是否具备可识别的事件和无事件随访。影像预处理进展不能补足临床标签。

当前仍为35条数值型RN时间、125条未知、0条已核实阴性，未拟合模型或计算AUC。46个FLAIR配对候选也不是最终建模样本数。没有联系原作者或请求非公开病例数据。

方法来源：[NiBabel的NIfTI仿射选择](https://nipy.org/nibabel/nifti_images.html)、[NIfTI qform/sform规范](https://nifti.nimh.nih.gov/nifti-1/documentation/nifti1fields/nifti1fields_pages/qsform.html/document_view.html)、[NIfTI FAQ](https://nifti.nimh.nih.gov/nifti-1/documentation/faq/index.html)。原始数据：[OpenBTAI/MOLAB](https://molab.es/datasets-brain-metastasis-1/)，各归档地址及许可沿用项目来源清单。
