# 第11步：改题获批后的基础临床模型

日期：2026-10-29（北京时间；执行记录使用UTC）。用户明确批准改题和本步工作。**已完成真实模型拟合及患者分组内部验证；结果较弱，不能作为有效鉴别模型。下一阶段等待批准。**

## 当前研究问题与纳入

高级别胶质瘤治疗后残余/复发肿瘤与治疗相关改变的探索性鉴别。使用UCSD-PTGBM官方临床v3和negative-case明细。全部243次扫描、178名患者纳入；年龄20–88岁、性别无缺失，未删例或插补。肿瘤192次（150名患者），治疗相关改变51次（39名患者），11名患者跨类。原脑转移瘤OpenBTAI队列不合并，其未来RN风险模型仍未训练。

51条标签0为清单明确记录；192条标签1由官方243=192+51完整分组补集推导。该标签体系不是逐例病理金标准。源临床诊断包含235条Glioblastoma及8条其他文本；一条Grade 5异常文本原样保留并标记，不作为输入，不据此声称重新病理分类。网站与下载清单的RN/其他亚型计数差异仍未解决，广义分组总数一致；本步不做RN单亚型建模。

## 固定模型与验证

方案`ucsd_clinical_baseline_protocol.md`在首次拟合前写入。只用年龄和出生性别（Male=1，Female=0）。年龄只在各训练折标准化，L2 Logistic回归C=1、lbfgs、max_iter=2000，无调参或类别加权。固定5折StratifiedGroupKFold，种子20261029。患者所有扫描保持同折；患者重叠0、所有243次扫描均有且仅有一次OOF预测，各折验证集48/48/48/49/50次扫描。没有独立外部测试集。

对照为每个训练折的肿瘤比例，为对应验证折赋恒定概率。对照OOF AUC略低于0.5来自不同折的训练比例略异，不表明一个恒定预测器有可用的排序能力。所有性能均为时间点级；bootstrap按患者整簇抽样2000次，保留其全部扫描，固定OOF概率。区间仅反映这组预测的患者抽样不确定性，不涵盖重新拟合/划分的全部变异。

| 指标 | 年龄+性别OOF | 患者簇bootstrap 95%区间 | 训练折比例对照OOF |
| --- | ---: | --- | ---: |
| ROC AUC | 0.5755 | 0.4671–0.6807 | 0.4881 |
| 肿瘤类AP | 0.8335 | 0.7596–0.9027 | 0.7857 |
| 治疗相关改变类AP | 0.2762 | 0.1830–0.4440 | 0.2058 |
| Brier评分（越低越好） | 0.1649 | 0.1310–0.2011 | 0.1659 |

Logistic减对照的Brier差为-0.00096，95%区间-0.01115至0.00935，跨0，未支持明确增益。肿瘤占比79.01%，所以肿瘤AP约0.83不能单独解释为优秀表现。

固定0.5阈值：肿瘤敏感度98.44%，治疗改变特异度0.00%，平衡准确率49.22%，准确率77.78%（全部判肿瘤即有79.01%准确率）。

| 真实类别 | 预测治疗改变 | 预测肿瘤 |
| --- | ---: | ---: |
| 治疗相关改变 | 0 | 51 |
| 残余/复发肿瘤 | 3 | 189 |

## 本步失败/受限原因

程序和分组检查成功，但仅年龄、性别的模型未达到有用的鉴别表现：AUC接近随机、区间跨0.5，0.5阈值未识别任何治疗改变，概率误差也未明确优于对照。不能因投稿目标较低就把这一结果称为“够用”。

可直接观察到的限制是只有两个人口学变量、肿瘤类别占约79%、治疗改变仅39名患者以及单中心内部验证。尚不能凭这些结果证明具体生物学原因，也不能预设MRI一定改善效果。推导标签、亚型版本差异和混合组织学限制解释；不通过改标签、换随机种子或搜索阈值来美化结果。全队列系数只作描述，未进行独立危险因素、因果或临床有效性推断。

## 可复现文件与检查

- `data/processed/ucsd_clinical_baseline_cohort.csv`：243条纳入记录、原始文本、来源行号和批准标记。
- `data/processed/ucsd_clinical_oof_predictions.csv`：逐例验证折、OOF概率及对照概率。
- `notebooks/11_ucsd_clinical_baseline.ipynb`：实际进程内ipykernel执行，5个代码单元、0错误；`reports/kernel_execution_11.json`保留收据。不宣称单独Jupyter服务器或浏览器前端经过验证。
- `reports/ucsd_clinical_baseline/`：完整指标、患者折清单、校准分组和最终系数；保存源数据、方案及分析代码SHA256。
- `outputs/ucsd-clinical-baseline-20261029/UCSD_Clinical_Baseline.xlsx`：Summary、Timepoints、Folds三页；243条数据及OOF结果，误差/计数/阈值汇总使用Excel公式，ROC/AP及区间由Python计算。修改Excel不会重训模型，正式复算须重跑Notebook及工作簿构建器。
- 同目录PNG/PDF为真实OOF ROC、PR和校准图。

```bash
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_11.json notebooks/11_ucsd_clinical_baseline.ipynb
python scripts/make_ucsd_baseline_deliverables.py
python -m unittest discover -s tests -p 'test_ucsd_clinical_baseline.py' -v
```

工作簿由`build_ucsd_baseline_workbook.mjs`通过artifact-tool生成，README记录构建方法。源数据固定字节未修改。针对源版本变化拒绝、患者隔离、折内缩放和未来/标签字段不能改变预测设置了检查。本步4项新检查及原有检查合计36项测试通过；保存后逐行核对Excel全部243条记录、缓存公式与Python一致，三页均已渲染审阅。验证记录见`reports/ucsd_clinical_baseline/artifact_verification.json`。

## 下一步计划：等待用户批准

建议下一步仅做**新队列MRI获取与特征可行性的小样本核查**：核对公开下载入口、临床ID对应关系、代表性样本序列及几何质量，制定不依赖类别专属肿瘤标注的ROI方案并检查是否适用于两组。公开的细胞性肿瘤掩膜或其体积可能直接暴露类别，不能直接拿来建鉴别模型。未确认公平、可复现的ROI和标签独立性之前不拟合MRI或融合模型。

本步未下载新队列MRI或启动该核查。用户批准后再执行，期间不扩展模型搜索。原题历史文件完整保留。

来源：[官方集合与v3更正说明](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/)、[数据论文](https://doi.org/10.1038/s41597-025-06499-z)。下载地址、许可和SHA256见原始来源清单及`DATA_LICENSES.md`。
