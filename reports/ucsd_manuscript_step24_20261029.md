# 第24步：诊断参考标准写作

用户批准继续下一节。本轮按V2大纲完成Methods 2.2 Reference standard（M4），英文后附对应中文，引用沿用2.1中的数据论文编号1。Word仅包含本节，不改动已确认的2.1、V2大纲或数据与模型结果。

## 完成内容

正文解释检查级结局：1为残余或复发肿瘤，0为治疗相关改变。公开negative-case表的51条ID匹配到源临床记录后赋为0；其余192条依据已发表243=192+51完整分组赋为1。隔离标识冲突记录和限定影像覆盖后保留原类别，没有依据模型预测重写标签。

参考诊断包含病理及临床/影像信息，并非每次检查均经病理证实。数据作者报告的45次病理证实肿瘤属于源完整192次肿瘤检查，未将45这个数量直接套用于本研究141次影像肿瘤检查。治疗改变包括假性进展、放射性坏死及非特异性治疗后改变；本研究未重新独立裁定诊断，结局为检查被赋予的当前状态。

公开明细的亚型数为NS 29、临床确认PsP 9、活检证实PsP 6、Radiation necrosis 7；源文章汇总分别为28、9、4、10。两者总数均为51。该差异在第10步已经发现，本轮再次读取原始工作簿确认。文中披露亚型差异、保留原条目及采用总数一致的广义二分类，未将全部治疗改变解释为纯放射性坏死或假性进展。以上细分计数存于核查JSON，避免在约150词的目标段落内堆叠来源不同的计数。

## 来源与核对

- 原始临床v3和negative-case表的SHA256与固定来源清单一致，原始文件未改写。
- 检查源243、隔离后238及影像182条记录的全部标签映射，共663条记录检查；这是三个嵌套数据表的核对次数，不是663个独立样本。对应人数分别178、176和135。
- 校验49个此前研究输入、表图、2.1交付文件及写作依据的哈希。没有模型重拟合、新检验或结果改选。
- 数据文章的Methods / Data collection及相关段落由已取得的PMC原始XML复核，并重新检索TCIA官方页面。Nature直开受重定向限制、TCIA直开曾报错、PMC随后触发验证码；已有原始全文和可检索的官方数据说明可支持本节，未由访问失败猜测诊断细节。
- 初次生成脚本使用了错误的历史队列文件名，导致文件读取中止；改为实际的`ucsd_clinical_baseline_cohort.csv`后完整核对通过。这是生成脚本路径错误，不涉及分析或标签变化。
- Word以Times New Roman 12 pt英文正文、单倍行距及页码呈现，中译紧随原段；无新图表。当前为分节审阅稿，完整投稿稿整合时统一处理全稿引用顺序和行号。

具体英文词数、页数、引用及逐页检查结果见`reports/ucsd_manuscript_step24/artifact_verification.json`。生成和核查方法：

```bash
python scripts/build_ucsd_methods_section22.py
python /path/to/documents/render_docx.py outputs/ucsd-manuscript-step24-20261029/UCSD_Manuscript_Methods_2_2_EN_ZH.docx --output_dir outputs/ucsd-manuscript-step24-20261029/docx_render --emit_pdf
python scripts/build_ucsd_methods_section22.py --verify
```

## 本步问题与下一步

亚型计数差异的原因仍未获得权威解释，病理与临床参考的混合性质也无法通过写作消除。当前处理保留数据版本与已批准的宽泛二分类，不据此修改标签或推断亚型性能；后续Discussion将讨论其对解释和推广的限制。

下一节建议撰写临床变量定义（M5–M6），交代年龄、性别、初始事件间隔、扫描前其他治疗及缺失指示，并与既有代码核对时间偏移和折内插补规则。本轮按逐阶段安排结束，等待用户批准。

来源：<https://pmc.ncbi.nlm.nih.gov/articles/PMC12886825/>；<https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/>；原始文件地址及SHA256见`methods_section22.json`。
