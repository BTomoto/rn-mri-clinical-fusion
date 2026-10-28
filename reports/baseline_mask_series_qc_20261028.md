# 基线分割对应MRI全序列质控

完成日期：2026-10-28。范围为当前54个基线掩膜候选（41名患者）、48组患者—日期检查的48个掩膜对应序列；不是全部所选MRI，也不覆盖这些检查的全部FLAIR序列。

## 结果

| 检查项 | 结果 |
| --- | ---: |
| DICOM切片 | 6,936 |
| 解压字节数 | 3,187,195,004 |
| 文件大小、CRC32、SHA256全部匹配 | 6,936 |
| 像素均可读取且形状与头信息一致 | 6,936 |
| 非有限像素 / 重复SOP UID / 目录日期不一致 | 0 / 0 / 0 |
| 规则单帧空间堆栈 | 48 |
| 层间距标签与空间位置不一致 | 26 |
| 常量切片 | 3 |
| 投影或重建序列 | 7 |
| 分割网格匹配病灶（≤0.001体素） | 42 |
| 超出网格容差、保留待复核病灶 | 12 |

全部54个病灶的目标体素均在对应影像的连续坐标视野内；目标体素在常量切片上的数量为0。这些结果支持技术定位复核，不构成解剖质量、运动伪影或RN诊断判断。没有病灶因此被自动纳入或排除建模。

## 来源与恢复

原16个影像分卷均恢复并逐个核验归档SHA256。从中仅提取本轮所需6,816张，再使用上一轮新增的120张40093/19010113切片，合计6,936张。每张与此前下载清单的SHA256一致。全项目所选42,385张的逐文件质控仍未完成，恢复归档本身也不等于完成质控。

10组掩膜名称与DICOM目录有标点差异，涉及11个病灶，例如`AXIAL_+C`对应`AXIAL_C`，以及`sp_0.7`对应`sp0.7`。严格按字符串会漏掉1,819张，因此最初估计5,137张修正为6,936张。当前43条病灶名称精确对应、11条为唯一的标点/大小写变体对应；没有模糊匹配、改写源文件名或任意选择多个候选。两侧名称和匹配规则均保留，坐标检验独立进行。

完整源成员清单保存为`data/metadata/baseline_qc/mask_series_members.jsonl.gz`，解压内容SHA256为`4265a67e6e34644153502b5c48d34c4ed521a20ac8689ff68348a03152f8b4c4`。逐切片结果保存为`cohort_dicom_file_qc.csv.gz`，可由pandas直接读取；压缩仅用于存储，不省略记录。序列和病灶明细保留为普通CSV。

## 仿射算法修正

本轮发现，先前取相邻切片位移中位数构造第三轴，在部分扫描仪舍入的坐标上会累积微小误差。现依NiBabel多切片公式，以排序后首末切片位置差除以间隔数构造第三轴；全部中间切片仍参与残差检查，最大残差约0.001171 mm。相邻层法向间距中位数仍用于间距报告和不规则缺层检查。

这是一项坐标计算修正，没有修改DICOM、NIfTI或诊断标签，也没有放宽0.001体素网格容差。修正前的临时核查为37个网格匹配，修正后为42个；前者未作为正式队列结果发布。为回归验证重新执行Notebook05、06、07；06的技术结果随当前实现更新。上轮Excel与报告保留为历史快照，本轮Excel及Notebook07是本范围当前结果。

## 需要复核的12个病灶

以下为完整体积8个角点经最佳整数轴翻转/置换后，剩余连续坐标差异的最大值。角点毫米误差采用物理空间欧氏距离；不能直接把它解释为病灶边界误差或临床不可用。

| 病灶 | 最大角点差异（体素） | 最大角点差异（mm） |
| --- | ---: | ---: |
| 20034_L1 | 0.001223 | 0.001236 |
| 20034_L2 | 0.001223 | 0.001236 |
| 40011_L2 | 0.008304 | 0.005856 |
| 40074_L1 | 0.001009 | 0.000743 |
| 40074_L2 | 0.001009 | 0.000743 |
| 40084_L1 | 0.005824 | 0.007623 |
| 40084_L2 | 0.148736 | 0.104119 |
| 40100_L1 | 0.002077 | 0.001056 |
| 40102_L1 | 0.001298 | 0.000909 |
| 40133_L1 | 0.014692 | 0.013250 |
| 40156_L1 | 0.087364 | 0.061156 |
| 40185_L1 | 0.026379 | 0.034294 |

常量切片位于40102/19000101的MPR序列（InstanceNumber386），以及40184/19000101的Ax_cube_T1（InstanceNumber125、126），像素均为0。InstanceNumber仅用于定位报告，没有用于排序。这些切片的成因、完整覆盖及图像伪影仍待专门审阅。

26个层间距标签差异按原值保留，构造空间网格使用实际位置，不覆写SpacingBetweenSlices。7个掩膜对应序列含投影/重建提示，后续影像组学需核实与原始采集的关系。全部文件ContrastBolusAgent为空，不能据此推定给药状态或时间；本轮也没有认定全部序列为已验证的增强采集。

## 重现与验证

```bash
python scripts/restore_sources.py
# 已有16个分卷可放在dist/restored_mri或原dist目录；只解压所需序列。
python scripts/restore_baseline_mask_series.py
# 没有分卷时可用官方成员下载：
# python scripts/restore_baseline_mask_series.py --download-missing
python scripts/run_notebooks_kernel.py notebooks/05_endpoint_versions_and_followup.ipynb notebooks/06_additional_baseline_imaging_qc.ipynb notebooks/07_baseline_mask_series_qc.ipynb
python scripts/make_baseline_qc_workbook_input.py
python -m unittest discover -s tests -v
```

Excel由`build_baseline_qc_workbook.mjs`使用artifact-tool生成，含Summary、Lesions、Series、Files四页；Files包含全部6,936行切片，公式汇总与CSV核对，四页均已渲染检查。Python输入生成脚本不直接创建Excel，导出需要提供artifact-tool的Node环境。

05—07均以进程内ipykernel执行，每份5个代码单元，无错误。27项测试通过；新增测试覆盖标点变体歧义拒绝，以及首末切片锚定避免中位增量舍入累计。尚未验证独立内核服务器或浏览器前端。

## 下一步

继续核查12个病灶的NIfTI仿射、DICOM位置精度及转换来源，保留来源坐标，不直接重采样。随后恢复对应FLAIR序列，核实采集类型和时间，再制定跨序列配准及图像质量审阅方案。

结局状态保持75名患者、160个病灶、35个数值型RN时间、125个未知、0个已核实阴性。54个基线候选仍是候选，42个网格匹配不是最终纳入数。未拟合模型，未计算AUC。

方法来源：[NiBabel多切片仿射推导](https://nipy.org/nibabel/dicom/dicom_orientation.html#getting-a-3d-affine-from-a-dicom-slice-or-list-of-slices)、[DICOM Image Plane Module](https://dicom.nema.org/medical/dicom/2026c/output/chtml/part03/sect_C.7.6.2.html)。原始数据：[OpenBTAI/MOLAB](https://molab.es/datasets-brain-metastasis-1/)；各官方归档、许可和成员来源保留在项目来源清单。
