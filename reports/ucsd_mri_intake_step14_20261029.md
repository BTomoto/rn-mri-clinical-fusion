# 第14步结果：MRI接收与质控准备完成，实际影像仍待获取

本步用户已批准。完成日期：2026-10-29（北京时间）。本步完成了可复用的文件接收、技术质控程序及运行验证；**未完成真实MRI像素质控、ROI确认或MRI模型分析**。

## 实际检查结果

当前工作区未找到两例指定UCSD实际NIfTI，项目文件清单也未提供新增影像。旧OpenBTAI分割压缩包是另一队列，未用于本研究。执行默认接收目录的结果为：

| 项目 | 结果 |
| --- | --- |
| 两例扩展文件清单 | 12项（每例6项） |
| 唯一找到的预期实际文件 | 0 |
| 完整体素解码 | 0 |
| 通过技术检查 | 0 |
| 最小两份FLAIR批次通过 | 否 |
| 解剖配准/预测ROI完成 | 否/否 |
| 新增MRI特征或模型 | 无 |

实际运行的逐项结果见`ucsd_mri_intake/sample_file_checklist.csv`及`intake_receipt.json`，CSV可用Excel打开。12项是预期文件清单，不是新增样本数据。已有临床Excel、逐例预测、模型代码和Notebook13均保持与第13步发布版本字节一致；不再重跑临床模型或修改其指标。

## 本步具体完成的工作

固定接收规则后实现`src/rn_public/ucsd_mri_intake.py`：精确文件名及病例目录匹配，拦截同名重复/内容重复/符号链接/0字节；gzip完整性与SHA256记录；完整3D缩放体素解码；非有限及常量值检查；单位换算；qform/sform与跨序列网格比较。遇到问题保留原因，不自动改头、重采样或猜测标签。

普通BraTS分割仅检查数值/网格：空掩膜不变成零肿瘤预测特征，未知数值不推测其组织含义。TCT/ECT/NECT细胞性肿瘤参考掩膜只登记为排除文件，不读取其体素。任何技术通过均不能自动授权预测ROI；人工解剖审阅、标签字典、标注盲法及两组同一分割规则仍须核实。

Notebook14实际通过进程内Jupyter/ipykernel执行，5个代码单元、0错误；独立内核服务器及浏览器前端未验证。全项目57项自动测试通过、0失败、0跳过，其中新增10项故障测试。软件测试使用临时小数组，测试后删除，不是研究样本，也不计入影像获取或质控结果。回执见`software_test_receipt.json`、`../kernel_execution_14.json`及`artifact_verification.json`。

本步没有真实影像，因此没有生成示例病灶图、影像统计量、ROI体积、影像AUC或MRI增量结论；没有新写一份包含“模拟研究数据”的Excel。

## 未能完成真实影像核查的原因

直接原因是两例实际文件尚未到位。第13步已取得官方两文件下载参数，但执行环境连接公布FASP端口返回网络不可达，且未安装Aspera客户端，实际传输未启动；本步没有在环境未变时重复相同的失败连接。先前传输失败的事实来自第13步保存回执，不是本步新测量。

目录/文件名清单、HTTP 201下载参数以及软件测试通过，都不能替代真实体素。这是数据获取依赖，不能归因于影像没有鉴别能力，也不能由此推断当前研究一定无法继续。即使文件技术通过，参考标签及标注过程可能造成的偏倚仍须单独说明。

## 下一步计划与用户需要做的事

1. 先按[两例本地获取说明](ucsd_clinical_revalidation/MRI_SAMPLE_DOWNLOAD_CN.md)从[TCIA官方集合页](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/)进入**BraTS-GLI 2024 Test Data**。最小先取得`UCSD-PTGBM-0001_01_FLAIR.nii.gz`和`UCSD-PTGBM-0003_01_FLAIR.nii.gz`两个真实文件，保留原始文件名；可将两病例目录打包提供。无需先下载完整队列，也无需提供GitHub或TCIA个人密码。
2. 文件到位后，在下一步批准范围内执行完整性/体素/几何核查，输出实际多平面审阅图和问题清单。两例仅作技术试验，不估计模型性能。
3. 再补每例T1pre、T1post、T2、ADC_vendor、普通BraTS分割及官方标签说明，核查ROI可行性；当前不扩大为全队列下载或融合模型训练。

本步准备工作已完成，可以进入“真实两例MRI技术核查”；**该阶段开始依赖真实文件到位及用户批准**。未获得文件前，不能用重复临床建模来替代MRI验证。若本地也无法下载，可先报告具体错误再决定研究范围。

## 复现

在项目根目录、已安装requirements.txt的Python环境运行：

```bash
python scripts/audit_ucsd_mri_intake.py
python -m unittest discover -s tests -p 'test_ucsd_mri_intake.py' -v
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_14.json notebooks/14_ucsd_mri_intake_and_qc.ipynb
python scripts/verify_ucsd_mri_intake_artifacts.py
```

默认接收目录`data/imaging/ucsd_samples/`已被Git忽略，避免将MRI大文件误提交。命令支持`--input-root /实际接收目录`及`--output-root /独立结果目录`；输入与输出不可重叠。命令行返回码2表示缺文件或最小批次未通过，并非程序崩溃；读取回执了解原因。返回码0仅表示两份FLAIR通过技术筛查，不表示ROI或临床有效性通过。当前Notebook记录的是缺文件状态，取得真实文件后应重新执行并保留新版本。

软件规则及方法依据见[固定规则](ucsd_mri_intake_protocol.md)。原数据CC BY 4.0，保留数据DOI 10.7937/fwv2-dt74及描述论文DOI 10.1038/s41597-025-06499-z的引用。NiBabel官方说明强调头部载入存在延迟读取，完整像素与form检查各自保留；来源真实性不能由本地SHA256单独证明。
