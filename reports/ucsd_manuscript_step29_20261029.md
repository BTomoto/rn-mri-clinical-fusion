# 第29步：性能指标与条件不确定性写作

用户批准继续下一节。本轮按V2大纲完成M14–M15，即Methods 2.7 Performance metrics and conditional uncertainty。英文后逐段附对应中文，另附接续编号8的原生Word公式，定义唯一主要Fusion−M1 ROC AUC增量。实际词数及两页排版核查见本节JSON与验证回执；未改动此前正文或研究结果。

## 正文内容

M14说明将五折OOF概率合并，以检查为单位计算指标，不取五个折AUC的简单平均。主要比较是相同检查上的Fusion−M1 ROC AUC差。两类分别报告AP，治疗相关改变的AP以该类为正类、以1减肿瘤概率作为评分；AP按召回率增量对精确率加权，不将其误写为PR曲线的梯形积分。Brier和log loss作为概率误差指标，较低较好。固定概率阈值0.5，大于或等于0.5判为肿瘤；计算混淆计数、两类识别、各类精确率、平衡准确率和准确率，没有阈值优化。

M15说明2000次患者聚类bootstrap尝试，seed=20261030，每次有放回抽取135组，整组保留所有检查；同组重复抽中则其检查也重复计入。所有模型用相同抽样索引做配对差值，OOF概率固定，不在抽样内重拟合模型或预处理。单类抽样不合格且不补抽；本次实际2000次均含两类，零跳过。

95%百分位区间明确仅用于ROC AUC、治疗相关改变AP、Brier和log loss及其配对差值，取第2.5及第97.5百分位。没有宣称肿瘤AP、准确率或每个阈值指标均有bootstrap区间。区间条件于已保存OOF预测，仅反映患者重采样的抽样不确定性，不覆盖完整训练与分折变异。Brier差的方向按Fusion−M1保留，负值有利于Fusion；未根据区间或指标方向改写主要比较，也未增加p值或多重检验结论。

## 实际核查

- 82份既有输入、模型结果、正文和计算依据文件的SHA256核对一致，原预测、bootstrap CSV与指标JSON未改写。
- 用独立算式核对四个主模型共60个原有指标值：AUC采用正负概率配对比较并计入平局0.5；AP用PR数组的召回率增量权重；Brier及自然对数损失用逐检查平均；阈值计数和敏感度/识别率、精确率、平衡准确率、准确率直接从标签与固定概率计算。与原指标一致。
- 读取2000×46的既有bootstrap表；44个指标或差值列的88个百分位端点与原JSON一致。5组比较×4指标×2000次，共40000个配对差值均与相同抽样行的两模型指标相减一致。
- 只重放已固定种子的抽样索引，核对全部2000次抽样的检查数及两类存在。患者组数始终为135次有放回选择，而检查数随组内扫描数量变化，范围159–218，不能写成每次固定抽182个独立扫描。
- 对预先用于本轮查核的第1、1000、2000次抽样，按固定OOF概率核对6个原记录版本×4项指标，共72个值；与原表一致。这里没有搜索较优抽样或重新训练模型。
- 原生公式对象、无公式图片、两组中英顺序、英文字符、词数和逐页渲染结果见`artifact_verification.json`。

## 问题与下一步

没有发现已保存指标、抽样计数、配对差值或区间端点的新不一致。写作核查时将笼统的“各指标均有区间”改为实际的四项区间指标范围，防止把未执行的计算写进论文。原方法的条件区间限制无法通过文字表述变成完整训练不确定性，本节已明确披露。

本节描述实际评价方法，未新增论文参考文献。scikit-learn 1.8官方AP、Brier和log loss文档作为实现核对依据保留在JSON；完整论文参考文献仍按已有计划整合。

下一节按M16撰写校准评估，说明OOF预测的分位分组、offset截距和带自由截距的校准斜率定义，并明确未用校准诊断重新校准或改变现有预测。按逐阶段安排，等待用户批准后继续。

## 文件

- `outputs/ucsd-manuscript-step29-20261029/UCSD_Manuscript_Methods_2_7_EN_ZH.docx`
- `outputs/ucsd-manuscript-step29-20261029/UCSD_Manuscript_Methods_2_7_EN.txt`
- `reports/ucsd_manuscript_step29/methods_section27.json`及`artifact_verification.json`
- `scripts/build_ucsd_methods_section27.py`：默认生成并核查；渲染审阅后用`--verify`保存验证回执。复用已核验OMML函数，未覆盖前节公式。

来源：Git内固定第18步方案、OOF预测、配对bootstrap表与指标JSON；<https://scikit-learn.org/1.8/modules/generated/sklearn.metrics.average_precision_score.html>；<https://scikit-learn.org/1.8/modules/generated/sklearn.metrics.brier_score_loss.html>；<https://scikit-learn.org/1.8/modules/generated/sklearn.metrics.log_loss.html>。
