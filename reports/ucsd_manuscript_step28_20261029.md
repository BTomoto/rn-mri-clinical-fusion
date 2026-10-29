# 第28步：固定模型与患者分组训练写作

用户批准继续下一节。本轮完成V2大纲M12–M13，即Methods 2.6 Model specification and grouped training。英文正文305词（157与148词），两组对应中文，共两页，另附接续编号7的原生可编辑Logistic概率公式。此次仅描述和核验既定分析，没有新训练或调整模型。

## 完成内容

M12分别说明M0的年龄/性别2项、M1的5项临床输入、MRI的8项固定影像特征、Fusion的5+8=13项特征级拼接。每个模型有截距，并以同一L2 Logistic框架比较不同输入集合。固定逆正则化强度C=1、lbfgs、最大2000次迭代、tol=0.0001、不加类别权重。代码在scikit-learn 1.8中以l1_ratio=0表示L2，未把库参数的版本变化误写为另一种惩罚。没有擅自将C解释为未经定义损失下的简单惩罚系数。Equation 7给出处理后特征向量对应的肿瘤概率，系数只用于预测，不作因果解释。

M13说明同182次检查、同五折、患者分组、启用打乱和固定种子20261029。源临床患者、BraTS患者及保守分组标识均不跨训练/验证折；病例—折清单在拟合前冻结，不按性能重新选择。年龄、时间变量和MRI特征在被纳入相应模型时仅从训练折学习缩放参数，时间填补沿用2.3，二分类不缩放。每次检查每个模型得到一个OOF肿瘤概率。没有调参、特征筛选、降维、过采样或交互扩展；验证仍是公开队列内部验证。

## 实际核查

- 原第18步锁定的协议、分析代码、四个输入文件和折清单SHA256均匹配。共78份此前交付、数据、结果或实现依据文件保持核对一致。
- 只实例化四个未拟合的模型对象读取固定参数，不调用fit。输入维数为2/5/8/13，Fusion的列集合和顺序为M1与MRI特征拼接，没有概率平均或第二层堆叠模型。
- 以固定StratifiedGroupKFold规则只重建分折，不拟合，182条折分配与已冻结清单完全一致。五折均含两类，三个患者标识体系全部隔离；182次检查各进入验证一次，队列135名源患者保持不变。
- 核对20个已保存折模型、140个非截距系数及列顺序。各模型在相应训练集的连续输入均值/总体标准差、缺失时间的训练中位数，与原参数一致；二分类输入按记录原样传递。
- 用已保存系数、截距和预处理参数，按Equation 7还原4模型×182检查=728个已有OOF概率，与原CSV最大绝对差约3.33×10^-16，仅为浮点舍入。没有重新估计系数、重算性能表、寻找更优折或替换原预测。
- 原生公式对象计数、英文字符、双语顺序、词数及两页渲染检查见`artifact_verification.json`。公式不是图片，编号接续前节1–6。

## 问题与下一步

本轮未发现模型输入、参数、分折或概率公式与既有结果的新不一致。没有独立外部验证、源标签与上游标注限制仍然存在；保持患者隔离不等于消除这些来源限制。论文未据此宣称临床可用或因果有效。

本节陈述本研究实际方法，未新增论文参考条目；软件参数含义对照scikit-learn 1.8官方文档，源地址存于JSON。全稿软件说明和引用在后续复现小节统一安排，不重复添加已规划软件文献。

下一节按M14–M15撰写性能指标与条件不确定性，明确主要Fusion−M1的AUC增量、两类AP、Brier/log loss和固定阈值指标，以及固定OOF预测的2000次患者聚类配对bootstrap区间。应区别患者抽样区间与重新训练/分折变异，不将现有区间写成外部验证。等待用户批准后继续。

## 文件与复现

- `outputs/ucsd-manuscript-step28-20261029/UCSD_Manuscript_Methods_2_6_EN_ZH.docx`
- `outputs/ucsd-manuscript-step28-20261029/UCSD_Manuscript_Methods_2_6_EN.txt`：仅英文叙述，公式以Word为准。
- `reports/ucsd_manuscript_step28/methods_section26.json`及`artifact_verification.json`
- `scripts/build_ucsd_methods_section26.py`：默认生成并核查；渲染审阅后以`--verify`写回执。复用上节已验证的OMML辅助函数，不覆盖上节文件。

实现说明：<https://scikit-learn.org/1.8/modules/generated/sklearn.linear_model.LogisticRegression.html>；<https://scikit-learn.org/1.8/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html>。原始研究方案、输入、折记录和OOF数据均在现有Git仓库。
