# 第10步：公开标签可行性核查

日期：2026-10-29。本步获批范围仅为公开标签可行性核查。**未训练模型，未下载新队列MRI，未更改原研究问题。下一阶段等待用户批准。**

## 本步完成了什么

1. 取得并核查此前未能读取的RN-D3补充材料，关闭这一访问缺口。
2. 从UCSD-PTGBM官方网站当前链接下载临床v3工作簿及51条negative-case分类明细，保留原始字节、来源、SHA256及许可信息。
3. 核对扫描ID与患者ID、亚型计数、重复时间点和候选二分类分组，生成243条可审阅记录。所有`use_for_model`和研究问题批准标记保持0。

## RN-D3附录核查结果及原题目未能推进的原因

通过Europe PMC公开补充材料接口取得705,029字节ZIP，SHA256为`b69dc975548e3bf52c886aea0b9a9a57b78404720808c98571d2572ac7e94ed4`，内含720,410字节`Data_Sheet_1.DOCX`。解析全部表格文字，并检查两张嵌入图。3张表分别为队列汇总、网络结构和超参数；2张图为训练曲线和分类器ROC。未观察到可与现有MOLAB病灶编号连接的标签表。

这不是附录访问失败：文件已经取得并核查。**本步未能补足原脑转移瘤RN风险预测标签的原因，是这份附录没有提供所需逐病灶事件/无事件随访对应表。** 原OpenBTAI数据仍有35条数值型RN时间、125条未知和0条已核实阴性。结论限于已经核查的文件，不宣称全网不存在其他标签。

补充材料只在可重下载的临时缓存中保存；Git中保留其地址、文件哈希、结构和审阅结果，不重发布原图表或全文。

## 新的公开标签来源：UCSD-PTGBM

本次使用的两个当前公开文件：

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| 临床v3：UCSD_PTGBM-clinical-information_v3_2026-12-Mar.xlsx | 93,648 | bbf40bbdd289266924869052806de4d7e8fc9ee73286cdc0cc066672ef5bb51d |
| details_of_negative_cases_TCIA.xlsx | 9,890 | 6d99db8ac1feac569e50c18ed214a1a761858fb8bfa614a29ec5f036946b96e4 |

临床文件包含243个唯一扫描时间点、178名患者。51条分类明细的扫描ID均可一一连接到临床v3，没有重复或未匹配ID。该数据库为高级别胶质瘤术后/治疗后资料，**不是脑转移瘤治疗前风险队列**。源文件部分诊断文本还有需要审阅的异常值（例如含Grade5的诊断文本），没有自行改写；下一阶段应核查纳入规则。

### RN亚型计数存在版本差异

| 亚型 | 官网/论文介绍 | 本次下载的明细 | 差异 |
| --- | ---: | ---: | ---: |
| NS（非特异性改变，保留原代码） | 28 | 29 | +1 |
| 临床确认PsP | 9 | 9 | 0 |
| 活检证实PsP | 4 | 6 | +2 |
| Radiation necrosis | 10 | 7 | -3 |
| 合计 | 51 | 51 | 0 |

7个RN时间点来自**4名患者**：0119（2次）、0147（2次）、0167（1次）、0172（2次），完整公开ID保留在数据表。不能把7次扫描当成7名独立患者，也不按官网10这个计数补造3条病例。

因此本步不建议立即用它单独训练RN分类模型：明确RN患者仅4名，患者分组验证会很不稳定，亚型计数差异也未解决。这是标签和独立患者数量的限制，不是模型AUC尚未调高的问题。未把其他扫描自动判成RN阴性。

### 可继续核查的替代问题

官网声明243个时间点由192个残余/复发肿瘤和51个仅有治疗相关改变的时间点构成。当前51条明细提供后者的ID；按这一明确的总分组，剩余192条可以形成**推导的肿瘤候选标签**。来源已逐行区分：51条为明细清单，192条为已发表分组的补集推导，不宣称每条均有个体病理证实。

| 候选类别 | 时间点数 | 涉及患者数 |
| --- | ---: | ---: |
| 残余/复发肿瘤候选 | 192 | 150 |
| 治疗相关改变 | 51 | 39 |

11名患者在不同时间点跨两类，150+39−11=178，因此后续验证必须按患者分组。这里的negative-case表示肿瘤类别的对照，**不是原项目的“未来不发生RN”阴性随访**。

## 下一步建议：需批准后才能开始

建议将问题调整为：**高级别胶质瘤治疗后残余/复发肿瘤与治疗相关改变的探索性鉴别**。这同时改变疾病对象（脑转移瘤→高级别胶质瘤）和任务（未来RN风险→当前影像状态鉴别），本步未执行这一调整。

若用户批准下一步：

1. 锁定纳入规则、243个时间点的标签来源和患者分组；遇到不能解决的标签核查问题则停止并报告。
2. 先跑预先指定的基础临床Logistic模型，以年龄、性别等扫描时已知变量起步，采用患者分组验证。不以高AUC为目标，不做为抬高结果而进行的大范围模型搜索。
3. 不使用未来死亡/随访资料，也不使用直接定义该标签的细胞性肿瘤分割体积作预测输入。加入MRI特征之前，另行确认不泄漏标签的ROI与特征方案。

如果不批准改变原研究问题，则保留原题目及已整理数据，当前仍不能以未知标签代替真值来训练原模型。原问题的进一步工作只能继续寻找可追溯的公开终点说明或标签来源。

## 本步文件与验证

- `notebooks/10_public_label_feasibility.ipynb`：5个代码单元通过进程内ipykernel执行，无错误。没有训练/验证模型或计算AUC。
- `data/raw/reference/ucsd_ptgbm_clinical_v3.xlsx`、`ucsd_ptgbm_negative_cases.xlsx`：原始文件未修改。
- `data/processed/ucsd_ptgbm_label_feasibility.csv`：243条候选记录，保留原临床行号、分类明细行号、原始亚型和推导标记；RN阴性未推定。
- `data/processed/ucsd_ptgbm_subtype_count_comparison.csv`：官网/论文介绍与实际文件的4类差异。
- `RN_Public_Label_Feasibility.xlsx`：Summary、Timepoints、Sources三页，含全部243条记录，公式汇总与原文件核对，三页已渲染检查。
- 来源下载器固定SHA256。源文件变化会停止，不覆盖已记录版本；临床工作簿Data Dictionary的稀疏超大使用范围未当作实际病例行。

```bash
python scripts/audit_public_label_feasibility.py
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_10.json notebooks/10_public_label_feasibility.ipynb
python scripts/make_label_audit_workbook_input.py
```

Excel由artifact-tool Node构建器导出。补充材料缓存缺失时脚本会从公开接口取得并核验；本步不需要任何登录或非公开数据。

本步以“结果—未解决原因—下一步计划”结束，**等待用户批准后再进入下一步**。

来源：[UCSD-PTGBM官方数据页](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/)、[临床v3](https://www.cancerimagingarchive.net/wp-content/uploads/UCSD_PTGBM-clinical-information_v3_2026-12-Mar.xlsx)、[分类明细](https://www.cancerimagingarchive.net/wp-content/uploads/details_of_negative_cases_TCIA.xlsx)、[数据论文](https://doi.org/10.1038/s41597-025-06499-z)、[Europe PMC补充材料接口](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13490108/supplementaryFiles?includeInlineImage=false)、[RN-D3论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC13490108/)。
