# 高级别胶质瘤治疗后肿瘤与治疗相关改变的探索性鉴别

公开UCSD-PTGBM数据二次分析项目。用户已明确批准从原脑转移瘤未来RN风险预测问题，调整为高级别胶质瘤治疗后残余/复发肿瘤与治疗相关改变的鉴别。仓库名保留以维持链接；原项目资料作为历史记录保留，不合并两队列。

**第18步已完成共同病例的临床、MRI与融合Logistic比较。** 同一182次扫描/135名患者、固定患者分组5折，M0/M1/MRI/Fusion的OOF AUC分别0.5255/0.6721/0.7625/0.7819。唯一主要比较Fusion−M1 AUC差为0.1098（患者聚类95%区间0.0214–0.2141），提示内部增量信号；Brier差区间跨0。固定0.5阈值只识别12/41次治疗改变，校准斜率0.6673，不能称临床可用。原ROI仍为主分析；腐蚀Fusion AUC=0.7881，相对原Fusion差值区间跨0，未改选较高版本。

见[第18步报告](reports/ucsd_fusion_step18_20261029.md)、[拟合前固定协议](reports/ucsd_fusion_protocol.md)、[Notebook18](notebooks/18_ucsd_clinical_mri_fusion.ipynb)、[Excel](outputs/ucsd-fusion-20261029/UCSD_Clinical_MRI_Fusion.xlsx)、[逐例OOF预测](data/processed/ucsd_fusion_oof.csv)、[指标与完整折参数](reports/ucsd_fusion/)。2,000次患者配对抽样全部有效，但固定OOF概率，不覆盖全部训练/分折不确定性。全项目79项测试通过；Notebook实际执行5单元、0错误；独立重建1,092个模型OOF概率通过。没有调参、特征筛选或阈值优化。

```bash
python scripts/run_ucsd_fusion.py --freeze-only
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_18.json notebooks/18_ucsd_clinical_mri_fusion.ipynb
```

第17步特征CSV足以重跑本阶段，不需再次下载MRI。下一阶段建议固定模型稳定性复核（重复患者分组验证及每患者单扫描敏感性），随后整理论文材料，等待用户批准。没有外部验证，标注盲法、8位强度、unknown空间单位与公开分组标签限制保留。

**第17步已完成批量有限影像特征与临床连接。** 实际取得并完整核验546份文件，共525.72 MB；182次扫描/135名源患者（141肿瘤、41治疗改变）全部提取8项固定特征，0次提取失败。另56次临床扫描未被当前镜像覆盖，仍保留在全238条状态表。182次腐蚀敏感性特征亦完整，FLAIR纹理对比度的绝对相对变化中位数15.29%、最大58.81%，提示边界依赖。没有训练MRI模型或计算AUC。

见[第17步报告](reports/ucsd_batch_features_step17_20261029.md)、[固定协议](reports/ucsd_batch_features_protocol.md)、[临床与影像CSV](data/processed/ucsd_clinical_image_features.csv)、[Notebook17](notebooks/17_ucsd_batch_image_features.ipynb)、[Excel](outputs/ucsd-batch-features-20261029/UCSD_Clinical_Image_Features.xlsx)、[实际文件QC与特征字典](reports/ucsd_batch_features/)。Notebook实际执行5单元、0错误，全项目73项测试通过。所有空间单位仍unknown，uint8及标注盲法限制保留，只研究该公开派生版本。下一阶段拟在共同病例上进行患者分组的临床/MRI/融合Logistic比较，等待用户批准。

新增528份源影像已保存为508.30 MB独立归档，528/528恢复核验通过；其余18份所需输入已在Git样本中。追加原影像未作为普通Git文件提交。[源包下载](https://chatgpt.com/library?file_id=libfile_3a6f9ba00eb08191b30cd19c0b1f1ecc&account_id=personal)需文件持有者账户权限；[恢复信息与SHA256](reports/ucsd_batch_features/source_archive_receipt.json)。也可由公开清单HTTPS重新取得，用户无需手动下载即可继续当前环境分析。

```bash
python scripts/restore_ucsd_batch_sources.py /path/to/UCSD_MRI_Batch_Additional_Sources_20261029.zip
python scripts/run_ucsd_batch_features.py
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_17.json notebooks/17_ucsd_batch_image_features.ipynb
```

**第16步已完成六例MRI技术扩展与统一ROI/强度处理试验。** 共6名不同源患者、两类各3例，36文件43.46 MB全部取得并解码；6例按普通BraTS全部正标签并集生成非空“源标注区域”，24份结构图像完成处理。原分位裁切会合并部分ROI高信号，最高26.33%；保留初始结果后追加不裁切线性缩放，24份成功，推荐下一阶段固定此方法。它是执行后工程修正，不是预注册或经独立样本证明最佳。尚未训练MRI模型或估计AUC。

见[第16步报告](reports/ucsd_roi_pilot_step16_20261029.md)、[原固定协议](reports/ucsd_roi_pilot_protocol.md)、[明确追加的强度修正](reports/ucsd_roi_pilot_intensity_amendment.md)、[Notebook16](notebooks/16_ucsd_roi_and_intensity_pilot.ipynb)、[Excel](outputs/ucsd-roi-pilot-20261029/UCSD_ROI_Intensity_Pilot.xlsx)及[派生二值ROI](data/processed/ucsd_roi_pilot_masks/)。Notebook实际执行5个单元、0错误；全项目67项测试通过。36份空间单位仍为unknown，30份强度图均uint8；不计算mL体积、毫米形态或定量ADC。源标注区域不是纯肿瘤，标注盲法未确认，技术成功不等于临床有效性。下一阶段建议按固定方法批量提取有限探索性特征，等待用户批准。

```bash
python scripts/run_ucsd_roi_pilot.py
python scripts/run_ucsd_intensity_followup.py
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_16.json notebooks/16_ucsd_roi_and_intensity_pilot.ipynb
python scripts/make_ucsd_roi_deliverables.py
python scripts/verify_ucsd_roi_artifacts.py
```

第15步记录：通过普通HTTPS镜像取得最初两例真实MRI，用户无需手动下载或安装Aspera。固定0002_01（治疗改变）与0005_01（肿瘤），12文件共14.25 MB全部完整下载、校验及解码；[实际NIfTI](data/samples/ucsd_mirror/)、[Notebook15](notebooks/15_ucsd_mri_mirror_samples.ipynb)、[Excel](outputs/ucsd-mri-mirror-20261029/UCSD_MRI_Mirror_Samples.xlsx)和[报告](reports/ucsd_mri_mirror_step15_20261029.md)均保留。三组真实图像预览已生成，5个代码单元实际执行成功，当时61项测试通过。

所有样本空间单位unknown，10份强度图像为uint8、范围0–255。因此12份均可解码且相对原生网格一致，但预设物理尺度检查仍未通过；未将步长1解释成1 mm，ADC不能作为原始定量值，普通分割尚未批准为预测ROI，没有训练MRI模型。镜像目录在既有238条临床队列内覆盖182次扫描/135名源患者（141肿瘤、41治疗改变），**这是候选目录数，当前实际只取得两例12文件**。本步用户已批准采用其他下载途径，不要求额外认证官方原文件来源；保留地址、编号与文件校验供正确连接及复现。

第14步缺文件状态是此前官方测试包0001_01/0003_01路线的历史结果，[原Notebook](notebooks/14_ucsd_mri_intake_and_qc.ipynb)及[报告](reports/ucsd_mri_intake_step14_20261029.md)未覆盖。当前改用镜像0002_01/0005_01；下一阶段建议扩大少量技术样本并固定统一ROI及强度处理方案，等待用户批准。

```bash
python scripts/download_ucsd_mirror_samples.py --refresh-inventory
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_15.json notebooks/15_ucsd_mri_mirror_samples.ipynb
python scripts/make_ucsd_mirror_deliverables.py
python scripts/verify_ucsd_mirror_artifacts.py
```

当前临床结果仍为第13步ID隔离后的重验：隔离5条双ID冲突扫描后，保留238次扫描、176名源患者。临床及BraTS患者ID均不跨验证折；相同病例/折上的M0（年龄＋性别）AUC=0.6124，M1（另加初始事件间隔与其他扫描前治疗）AUC=0.6790，Brier分别0.1640和0.1547。AUC成对差值0.0666的95%区间为−0.0499至0.1702，尚未确证增益。固定0.5阈值仅识别51次治疗改变中的5次，不声称临床可用。第14步核验8份关键临床资料与第13步发布版本字节一致。

本步在首次拟合前固定方案，无调参或阈值优化；46条间隔缺失只在训练折内填补，并加入缺失标记。唯一完整间隔资料敏感性分析为192次扫描/142名源患者，M0/M1 AUC为0.5211/0.6226，不能与主队列跨人群比较。见[第13步报告](reports/ucsd_clinical_revalidation_step13_20261029.md)、[固定方案](reports/ucsd_clinical_revalidation_protocol.md)、[Excel](outputs/ucsd-clinical-revalidation-20261029/UCSD_Clinical_Revalidation.xlsx)、[Notebook13](notebooks/13_ucsd_clinical_revalidation.ipynb)和[逐例OOF预测](data/processed/ucsd_clinical_revalidated_oof.csv)。

第13步曾重试两份指定FLAIR参数（HTTP 201），但执行环境连接公布的FASP端口返回网络不可达，实际传输未启动。第15步镜像已解决少量真实文件获取，见上方当前状态。将来MRI增量比较仍需在共同病例上重跑临床对照；当前临床结果不是与尚未建立的MRI模型比较。

```bash
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_13.json notebooks/13_ucsd_clinical_revalidation.ipynb
python scripts/make_ucsd_revalidation_deliverables.py
python scripts/probe_ucsd_mri_sample_transfer.py
python -m unittest discover -s tests -p 'test_ucsd_clinical_revalidation.py' -v
```

第13步Excel由`scripts/build_ucsd_revalidation_workbook.mjs`通过artifact-tool生成，设置`RN_PROJECT_ROOT`为项目绝对路径；修改Excel不会重新训练Python模型。Notebook和五页Excel已执行/核对，47项测试通过。后续阶段仍经用户批准后继续。

两份真实样本接收后运行以下命令，或用`--input-root`指定解压后的原名文件目录。缺文件或需复核时命令返回码2并保存blocked回执；返回码0也仅表示最小FLAIR批次技术通过。SHA256只作本地指纹，技术网格检查不能代替人工解剖审阅，预测ROI始终须另行核实。

```bash
python scripts/audit_ucsd_mri_intake.py
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_14.json notebooks/14_ucsd_mri_intake_and_qc.ipynb
python scripts/verify_ucsd_mri_intake_artifacts.py
```

## 第12步审计记录

第12步完成36个临床字段、时间和使用角色审阅，发现2个源患者5次扫描的临床/BraTS交叉映射，同一BraTS患者前缀跨第11步第4、5折。第11步指标保留为历史，不作为最终性能。原始源患者仍记178名，177个双ID连通组只是保守分组，不是真实身份修订；第13步采用隔离5条的方案重验。

本轮实际取得测试包59个病例目录并匹配临床ID，另取得一例治疗改变、一例肿瘤各23个文件名条目。46条均为符号链接，未解析目标或下载NIfTI，不能声称已完成像素、配准或ROI质控。两个公开下载包的授权和下载参数可取得，但无HTTP网关、本环境无Aspera客户端；主包目录请求超时。详见[第12步报告](reports/ucsd_clinical_mri_feasibility_step12_20261029.md)、[Excel](outputs/ucsd-feature-audit-20261029/UCSD_Clinical_MRI_Feasibility.xlsx)、[Notebook12](notebooks/12_ucsd_clinical_and_mri_feasibility.ipynb)与[技术样本清单](reports/ucsd_feature_audit/mri_sample_request.csv)。

第12步提出的ID隔离、临床变量/缺失规则冻结及重新验证，现已在第13步完成。第12步本身没有训练模型；其字段、访问收据及候选表保留以便追溯。

```bash
python scripts/audit_ucsd_clinical_features.py
python scripts/audit_ucsd_mri_access.py
python scripts/audit_ucsd_mri_inventory.py
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_12.json notebooks/12_ucsd_clinical_and_mri_feasibility.ipynb
python scripts/make_ucsd_feature_audit_deliverables.py
python -m unittest discover -s tests -p 'test_ucsd_feature_audit.py' -v
```

MRI脚本默认读取已保存收据；需要重新联网核查时显式加`--refresh`。访问令牌不保存到仓库。工作簿通过`scripts/build_ucsd_feature_audit_workbook.mjs`使用artifact-tool构建，保留全部36原始字段、候选列、问题及MRI层级；修改Excel不会自动重新建模。

## 第11步历史模型

第11步已拟合年龄/性别基础Logistic。243次扫描、178个临床源患者（192次肿瘤、51次治疗改变），固定5折、无调参。历史OOF AUC 0.5755，Brier 0.1649；这些结果尚未解决第12步发现的双ID问题。标签由negative-case清单和官方分组推导，不等同逐例病理真值。[历史报告](reports/ucsd_clinical_baseline_step11_20261029.md)、[固定方案](reports/ucsd_clinical_baseline_protocol.md)、[历史Excel](outputs/ucsd-clinical-baseline-20261029/UCSD_Clinical_Baseline.xlsx)及[Notebook11](notebooks/11_ucsd_clinical_baseline.ipynb)保留以追溯，旧执行器重跑只能复现历史设定，不解决ID冲突。

本步不需要恢复旧项目的大型MRI归档。在已安装`requirements.txt`的环境中运行：

```bash
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_11.json notebooks/11_ucsd_clinical_baseline.ipynb
python scripts/make_ucsd_baseline_deliverables.py
python -m unittest discover -s tests -p 'test_ucsd_clinical_baseline.py' -v
jupyter lab notebooks/11_ucsd_clinical_baseline.ipynb
```

Excel由`scripts/build_ucsd_baseline_workbook.mjs`使用`@oai/artifact-tool`构建；在装有该库的Node环境中设置`RN_PROJECT_ROOT`为项目绝对路径后执行。工作簿包含243条纳入数据和OOF预测，公式计算误差及汇总；修改Excel不会重新训练模型。Python是模型和指标的计算来源，完整环境版本见指标JSON。全队列系数只供重建和描述，不作独立危险因素结论。

## 原项目历史与改题依据

第10步RN-D3附录已取得并核查，未找到可连接原病灶的标签表。UCSD当前清单的RN仅7时间点/4患者，与官网介绍10不一致，所以未做RN单亚型模型。[第10步报告](reports/public_label_audit_step10_20261029.md)、[历史Excel](outputs/public-label-audit-20261029/RN_Public_Label_Feasibility.xlsx)和[Notebook10](notebooks/10_public_label_feasibility.ipynb)保留改题前状态。以下内容均指原OpenBTAI脑转移瘤项目。

**2026-10-29决定：暂不扩大全队列自动配准；原定风险模型不训练。** 三例刚性配准试验及一次步长受控重试已完成，仅10029_L2满足数值工程筛查，另外两例候选拒绝，临床接受及应用于分析均为0。公开临床文件重新获取后SHA256未变，125条未知结局及0条已核实阴性仍是原问题的关键限制。下一步优先核查完整公开终点来源，而不继续批量处理影像。见[报告](reports/registration_pilot_and_gate_20261029.md)、[Excel](outputs/registration-pilot-20261029/RN_Registration_Pilot_and_Model_Gate.xlsx)、[Notebook09](notebooks/09_registration_pilot_and_endpoint_gate.ipynb)。

2026-10-28阶段已恢复并逐文件检查40个基线FLAIR名称候选序列（1,391张），可关联46个病灶，8个未找到同期FLAIR名称候选。40158_L1约98.30%的目标体素中心在FLAIR坐标视野内，148个超出切片轴下界。12个网格差异继续保留，其中20034_L1、L2仅在qform敏感性检查中达到容差，没有据此替换仿射。见[该轮报告](reports/grid_precision_flair_20261028.md)、[Excel](outputs/flair-grid-qc-20261028/RN_FLAIR_Grid_Review.xlsx)、[Notebook08](notebooks/08_grid_precision_and_flair_pairs.ipynb)。该阶段未做跨序列配准，后续三例试验见09。

当前进一步核查54个基线分割候选的48个对应MRI序列，共6,936张切片，均可读取且通过几何连续性检查。42个病灶满足0.001体素网格容差，12个待复核；最大角点差异约0.104 mm。另记录26个层间距标签差异及3张常量切片。见[本轮报告](reports/baseline_mask_series_qc_20261028.md)、[当前质控Excel](outputs/baseline-qc-20261028/RN_Baseline_Mask_Series_QC.xlsx)、[Notebook07](notebooks/07_baseline_mask_series_qc.ipynb)。这不是全部MRI或FLAIR的完整临床质量核查，42个也不是最终纳入数。

最新一轮完成4组新增基线检查的逐文件技术质控：1,584张像素均可读取、28个规则堆栈通过技术检查；发现3个层间距标签与位置坐标不一致。40093_L3分割经两轴翻转与MRI网格匹配，无需插值。其余原归档影像仍未完成逐文件检查，跨序列配准和临床质量审阅仍待完成。见[本轮报告](reports/additional_imaging_qc_20261028.md)、[质控Excel](outputs/imaging-qc-20261028/RN_Additional_Imaging_QC.xlsx)、[Notebook 06](notebooks/06_additional_baseline_imaging_qc.ipynb)。

最新临床核查已改用原作者网站当前提供的Nov2023临床表：75名患者、160个病灶、35个数值型坏死时间、125个结局未知，首次SRS时间115条。按新治疗时间匹配有97个基线目录候选，其中54个病灶（41名患者）有实际基线掩膜，18个填写坏死时间。原Figshare临床表及先前结果保留为历史快照，不能与新版本混读。

最新文件：[临床版本与随访报告](reports/endpoint_followup_20261028.md)、[更新Excel](outputs/endpoint-followup-20261028/RN_Endpoint_Followup.xlsx)、[Notebook 05](notebooks/05_endpoint_versions_and_followup.ipynb)。仍未取得可确认空白RN为阴性的公开说明，未拟合风险模型。

2026-10-28进一步核查：直接读取373份NIfTI掩膜，得到591条病灶—时间记录；按掩膜日期与影像组学表交叉匹配，首次记录SRS前30天内有53个候选病灶（40名患者），其中17个填写坏死时间。早期仅按形态学表得到的21个匹配不能代表全部分割覆盖，因为该表97条日期使用了不同的年份编码。本项目未擅自改写这些日期。

新增 [核查报告](reports/readiness_audit_20261028.md)、[审阅Excel](outputs/readiness-20261028/RN_Readiness_Audit.xlsx) 和 [04核查Notebook](notebooks/04_readiness_audit.ipynb)。当前仍缺少逐病灶可追溯的阴性结局和诊断依据，未拟合预测模型。

本项目仅分析既有公开去标识数据，不新增招募或实施动物、细胞实验。数据原始来源为既往患者影像和临床记录；保留原始研究出处、许可及使用说明。

## 已保存的Figshare数据快照

- OpenBTAI原始临床表、形态学表、完整原始影像组学表和分割压缩包。
- 75名患者、160条临床病灶记录；32条脑坏死时间记录，128条状态未知。
- 六个官方DICOM压缩包的完整目录，形成635组患者—日期组合及3,111个序列目录。
- SRS前30天内的90个候选病灶，涉及59名患者。选择每个病灶最近的基线及窗口内最接近第90天的早期MRI，共107组患者—日期。
- MRI下载的完成状态、文件数和SHA256以 `data/metadata/downloaded_imaging.jsonl` 和 `reports/image_download_progress.json` 为准。
- Excel工作簿：`outputs/research-data/RN_Public_Data.xlsx`。MRI体素不嵌入Excel。

**这里的候选数量不能作为最终纳入数量。** 同日MRI需核实与SRS的先后；患者级影像目录需核实目标病灶可见性。最早记录的SRS并不自动证明完整治疗史。对照状态、脑坏死诊断依据和随访截止均须从可追溯的公开证据核实。空白脑坏死时间不编码为0。

## 项目结构

```text
data/raw/openbtai/     原始公开工作簿与分割ZIP
data/raw/reference/    UCSD-PTGBM原始临床与标签文件，及其他参考资料
data/metadata/         来源、校验和、ZIP目录、选择清单及已下载影像索引
data/processed/        患者、病灶、治疗、影像、特征和审核CSV
data/imaging/dicom/    原始MRI切片（大型数据，独立归档）
notebooks/            可在JupyterLab运行的分析记录
src/rn_public/        数据整理及HTTP Range下载代码
scripts/              下载、Notebook执行、工作簿生成和打包
reports/              可行性和下载状态记录
outputs/research-data/ Excel数据工作簿
tests/                来源与时间匹配完整性检查
```

## 运行

建议Python 3.12。安装 `requirements.txt` 后在项目根目录运行：

```bash
python scripts/restore_sources.py
python scripts/download_sources.py
python scripts/download_selected_images.py --workers 6
python scripts/run_notebooks.py
python -m unittest discover -s tests -v
jupyter lab notebooks/
```

下载器检查HTTP 206字节范围，并验证ZIP成员大小和CRC32。已下载文件通过CRC校验后可以跳过，不会把不完整文件当作完成。下载完后另外生成SHA256清单。

GitHub版本将超过3 MiB的原始表格、分割ZIP和完整目录索引保存在 `data/packed/` 的2 MiB分段文件中，解决连接的单次传输限制。`restore_sources.py`会先验证每段及合并压缩包的SHA256，再恢复原始文件并逐一验证SHA256。各Notebook也会自动执行恢复。临床分析CSV、Excel工作簿及代码可直接浏览。该分段包包含原始表格和索引；原始MRI另存为原16个分卷和1个新增基线追加包。

## Notebook顺序

1. `00_data_access_and_provenance.ipynb`：来源、许可、校验和和数据恢复。
2. `01_cohort_curation_and_audit.ipynb`：队列整理、时间窗口与未知结局。
3. `02_imaging_download_integrity.ipynb`：下载清单与文件完整性。
4. `03_model_readiness_and_analysis_plan.ipynb`：数据准备状态及M0—M2比较设计。
5. `04_readiness_audit.ipynb`：逐例时间冲突、实际掩膜覆盖、体积核对及DICOM抽样。
6. `05_endpoint_versions_and_followup.ipynb`：原作者临床版本、逐项差异及180/365日资料覆盖；使用当前临床表。
7. `06_additional_baseline_imaging_qc.ipynb`：新增4组基线检查的全部切片、空间连续性及既有掩膜网格匹配。
8. `07_baseline_mask_series_qc.ipynb`：54个当前基线掩膜候选的完整对应序列，逐文件检查及网格误差明细。
9. `08_grid_precision_and_flair_pairs.ipynb`：12个坐标差异、FLAIR恢复及配对坐标视野核查。
10. `09_registration_pilot_and_endpoint_gate.ipynb`：三例刚性配准试验、失败保留、工程拒绝规则及公开终点条件核查。
11. `10_public_label_feasibility.ipynb`：RN-D3附录、UCSD公开文件标签及候选研究问题的可行性核查；未建模，等待批准。
12. `11_ucsd_clinical_baseline.ipynb`：改题获批后的UCSD队列、固定年龄/性别Logistic及患者分组OOF验证；本步完成，等待批准影像可行性核查。
13. `12_ucsd_clinical_and_mri_feasibility.ipynb`：完整36字段、未来信息隔离、双ID交叉、MRI公开目录和ROI方案核查；无新模型或像素质控。
14. `13_ucsd_clinical_revalidation.ipynb`：隔离5条后的M0/M1临床比较、患者簇成对区间、完整间隔资料敏感性分析和两例MRI传输重试记录。
15. `14_ucsd_mri_intake_and_qc.ipynb`：两例MRI精确接收、完整体素/几何质控及ROI边界；当前缺实际文件，真实质控未完成。
16. `15_ucsd_mri_mirror_samples.ipynb`：替代HTTPS镜像两例12文件实际下载、解码、相对网格、物理尺度问题、真实图像预览及238行覆盖表。
17. `16_ucsd_roi_and_intensity_pilot.ipynb`：六例36文件、统一源标注区域、24份结构图像处理、一次腐蚀诊断，以及明确标记为执行后增加的不裁切方案。

00—04保留普通Python顺序执行器验证的输出。05—16已使用进程内Jupyter/ipykernel执行，每份5个代码单元均成功，标准输出、标准错误及结果写回Notebook。05—07执行回执见 `reports/kernel_execution.json`，08—16分别独立保存对应的执行JSON。00—10未训练模型；11生成历史性能，12发现双ID问题，13完成隔离后的重新验证和扩展临床比较，14—16未拟合模型。

当前环境禁止常规独立内核所需的TCP/IPC通信。新增的进程内执行器不打开端口，但仍使用ipykernel和Jupyter消息队列；这不等于验证了独立内核服务器或浏览器前端。该模式仅运行可信项目Notebook，没有硬超时或独立进程隔离。Notebook也可在正常JupyterLab环境中重跑。requirements.txt已加入本轮实际验证的pydicom和nibabel版本。先前的抽样和结构核查可依次运行：

```bash
python scripts/audit_dicom_samples.py
python scripts/audit_readiness.py
python scripts/run_notebooks.py notebooks/04_readiness_audit.ipynb
```

DICOM脚本仅抽取每个选定目录按ZIP顺序排列的首尾文件，核验CRC和SHA256并读取头信息；不是全部切片的像素、空间连续性或临床质量核查。掩膜标签的组织成分不作为RN诊断标签。

当前临床表的重现命令：

```bash
python scripts/download_molab_tables.py
python scripts/audit_endpoint_followup.py
python scripts/run_notebooks_kernel.py
```

该下载器核验当前记录的SHA256；若作者更新了源文件会停止，避免覆盖已记录版本。作者整套Excel包的Sept2023临床表与直接按钮的Nov2023临床表共同临床字段一致，但二进制不同。作者网站499条Total影像组学记录与Figshare的591条不能直接互换；当前候选特征保留Figshare版本标识。完整建模前仍需结局核实及影像质控。

进程内执行器默认只运行05，也可传入明确的Notebook路径。02的完整逐文件检查需要先恢复大型MRI文件；仅有Git仓库中的下载索引不能代替这些本地文件。

本轮新增影像技术质控可重现为：

```bash
python scripts/download_current_baselines.py
python scripts/run_notebooks_kernel.py notebooks/05_endpoint_versions_and_followup.ipynb notebooks/06_additional_baseline_imaging_qc.ipynb
```

若已恢复追加归档，可以跳过下载。脚本支持`data/imaging/current_baseline_addition/`暂存目录与归档中的`data/imaging/dicom/`路径。分割来源仍是原Figshare掩膜，标签不编码RN；技术质控不补足结局证据。

当前54个候选的分割对应序列核查：

```bash
python scripts/restore_baseline_mask_series.py --download-missing
python scripts/run_notebooks_kernel.py notebooks/05_endpoint_versions_and_followup.ipynb notebooks/06_additional_baseline_imaging_qc.ipynb notebooks/07_baseline_mask_series_qc.ipynb
```

若已有16个归档分卷可放在`dist/restored_mri/`，不加下载参数即可按哈希恢复所需成员。名称仅允许精确或唯一标点/大小写变体对应，并独立验证坐标。多切片仿射现用首末位置差构造第三轴，避免相邻位移中位数舍入误差累计；仍检查每层残差。逐切片CSV及成员清单用gzip无损保存，pandas可直接读取；解压副本可由脚本重建。本轮Excel为当前54个候选的结果，上一轮Excel保留为历史快照。

FLAIR与坐标差异复核：

```bash
python scripts/restore_baseline_flair.py --download-missing
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_08.json notebooks/08_grid_precision_and_flair_pairs.ipynb
```

08需要先恢复对应基线T1序列。FLAIR名称筛选、相同FrameOfReferenceUID、坐标视野比例均不等于已完成解剖对齐或临床质量核查。38个FLAIR候选存在规则采集层间隙。当前未改变源仿射、分割或最终纳入标记；qform结果仅作敏感性诊断。

三例方法试验使用SimpleITK2.5.6（已固定到requirements），需恢复归档第01/15分卷中的所需793张切片。09可重跑试验，并单独保存执行回执：

```bash
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_09.json notebooks/09_registration_pilot_and_endpoint_gate.ipynb
```

候选变换均未用于正式分析。2mm线性插值仅用于方法试验与派生审阅图，不恢复FLAIR层间隙或视野外组织。首轮失败及当前结果分别保留；不把优化器收敛、较好的坐标覆盖或数值筛查当作临床对齐通过。

## 后续影像与模型分析

需要先核实DICOM序列、完成T1增强与FLAIR配准、定位并分割目标病灶、逐例核验脑坏死终点及无事件随访，再确定主要预测期限。

基线临床模型、影像融合模型及可选纵向模型必须采用相同预测人群、期限及患者分组验证。死亡按竞争事件处理，不把提前死亡直接编码为无脑坏死。特征筛选、缺失值处理及调参只在训练折内完成。事件数量有限，不预先选择复杂深度网络。

UCSD、Yale和PROTEAS未提供本项目已核实可用的同终点外部验证队列；不可将它们的体积分割标签或零散神经症状文字替代放射性脑坏死诊断。

## GitHub与大型数据

临床版本更新后，另补齐4组基线MRI，共1,584个DICOM文件，约684.7 MB解压数据，单独生成约238 MB追加包。原16个MRI分卷保留；累计所选影像为42,385个DICOM、111组患者—日期、63名患者。追加包索引和SHA256见 `data/metadata/endpoint_followup/additional_baseline_imaging.jsonl`、`reports/additional_baseline_imaging.json`。可用 `python scripts/download_current_baselines.py` 从官方Figshare原始ZIP重新取得。完成下载校验不等于完整影像质控。

原作者整套Excel包的版本差异可运行 `python scripts/audit_molab_package.py` 重现；该命令会下载并核验已固定校验和的作者Excel包，报告499条与591条Total记录的覆盖差异，不替换现有分析特征。

代码、Notebook、Excel、原始表格及CSV属于主仓库。原始MRI需要独立的Release附件或其他适合大型文件的存储，不能作为超过100 MiB的普通Git文件直接提交。
保留下载URL和成员校验信息用于完整恢复。不要把“已有下载清单”表述为“所有MRI已上传GitHub”；以实际上传回执为准。

## 来源

- Ocaña-Tienda et al. *Scientific Data* (2023). DOI: https://doi.org/10.1038/s41597-023-02123-0
- OpenBTAI/MOLAB： https://molab.es/datasets-brain-metastasis-1/
- 临床数据： https://doi.org/10.6084/m9.figshare.22270933
- UCSD： https://www.cancerimagingarchive.net/collection/ucsd-bmets-longitudinal/
- Yale： https://www.cancerimagingarchive.net/collection/yale-brain-mets-longitudinal/
- PROTEAS v5： https://zenodo.org/records/23171182

数据许可见 `DATA_LICENSES.md` 和各来源原始元数据。
