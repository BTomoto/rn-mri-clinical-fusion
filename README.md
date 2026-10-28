# MRI–clinical fusion for radiation-necrosis research

公开数据库二次分析项目：脑转移瘤放疗后放射性脑坏死的探索性风险预测。

**当前版本完成数据获取、结构化整理和可行性核验；尚未完成临床预测模型。**

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
data/raw/reference/    其他候选数据库的临床资料，供可行性核验
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

GitHub版本将超过3 MiB的原始表格、分割ZIP和完整目录索引保存在 `data/packed/` 的2 MiB分段文件中，解决连接的单次传输限制。`restore_sources.py`会先验证每段及合并压缩包的SHA256，再恢复原始文件并逐一验证SHA256。各Notebook也会自动执行恢复。临床分析CSV、Excel工作簿及代码可直接浏览。该分段包包含原始表格和索引，原始MRI仍是单独的16个大文件分卷。

## Notebook顺序

1. `00_data_access_and_provenance.ipynb`：来源、许可、校验和和数据恢复。
2. `01_cohort_curation_and_audit.ipynb`：队列整理、时间窗口与未知结局。
3. `02_imaging_download_integrity.ipynb`：下载清单与文件完整性。
4. `03_model_readiness_and_analysis_plan.ipynb`：数据准备状态及M0—M2比较设计。
5. `04_readiness_audit.ipynb`：逐例时间冲突、实际掩膜覆盖、体积核对及DICOM抽样。
6. `05_endpoint_versions_and_followup.ipynb`：原作者临床版本、逐项差异及180/365日资料覆盖；使用当前临床表。

已执行Notebook输出由普通Python顺序执行器生成，未使用Jupyter内核。所有代码单元均为普通Python，可在JupyterLab重新运行。未生成或宣称任何模型AUC、校准或临床验证结果。

新增04也采用上述普通Python执行器验证。曾尝试nbclient启动Jupyter内核，但当前执行环境的网络接口/内核通信权限使内核启动失败，未宣称内核执行成功。Notebook可以在具备正常Jupyter环境的机器中重新运行。重新运行影像核查需额外安装 `pydicom>=3,<4` 和 `nibabel>=5,<6`。完整核查可依次运行：

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
python scripts/run_notebooks.py notebooks/05_endpoint_versions_and_followup.ipynb
```

该下载器核验当前记录的SHA256；若作者更新了源文件会停止，避免覆盖已记录版本。作者整套Excel包的Sept2023临床表与直接按钮的Nov2023临床表共同临床字段一致，但二进制不同。作者网站499条Total影像组学记录与Figshare的591条不能直接互换；当前候选特征保留Figshare版本标识。完整建模前仍需结局核实及影像质控。

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
