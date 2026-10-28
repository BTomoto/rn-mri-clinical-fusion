# 配准方法试验与原定模型的条件核查

日期：2026-10-29。本轮完成三例T1/FLAIR刚性配准方法试验，并复核公开临床文件及相关论文/代码。当前决定：**不采用失败候选变换，暂不扩大全队列自动配准；原定M0—M2风险模型仍不训练。**

## 来源恢复与选例

项目代码和既有结果从GitHub恢复；只恢复本轮所需MRI。原归档第01、15分卷均通过其既有SHA256校验，从中恢复793个DICOM（260,023,270字节），每张均与原下载清单SHA256一致。未覆盖或修改原始影像、NIfTI分割、临床表或纳入标记。

三例事先按影像条件选择，没有使用RN结局选例：10005_L1为常规厚层FLAIR，10029_L2为3D FLAIR，40158_L1为此前发现的坐标视野边界病例。三例均属于既有sform网格匹配的候选。它们不是随机验证样本，不能据此估计全队列配准成功率。

## 配准与评估方法

使用SimpleITK2.5.6、Euler3D六参数刚性变换。DICOM列—行—切片数组按已验证空间位置排序，保留其物理空间；从RAS转换到SimpleITK的LPS。固定图像为T1，移动图像为FLAIR；保存的候选变换映射**固定T1的物理LPS点到移动FLAIR的物理LPS点**，也是重采样所需的输出到输入方向。

只为本方法试验做强度归一化和派生显示，不提取预测特征。正强度的1/99百分位用于归一化，固定图像归一化值>0.05作为粗强度前景；它不是脑分割或颅骨剥离。临时固定配准网格2mm，Mattes互信息50箱、随机采样20%、种子20261029、单线程，金字塔[4,2,1]、物理平滑[2,1,0]mm。初始化刚性参数为零，旋转中心为固定图像物理中心，未通过结局或目标病灶调参。

另在同一个3mm固定网格上，以全部固定强度前景评估负互信息和移动影像坐标视野重叠。负互信息越低越好。这是同一相似性函数的更完整数值检查，不是独立临床验证或外部验证。线性插值不能补回采集层间隙或视野外组织。

## 首轮失败与一次重试

首轮GradientDescent（学习率1、每层最多100次）在3例的全量负互信息均变差，尽管优化器报告收敛。最大平移范数约120.6mm，不能据收敛标志接受变换。该轮CSV、JSON、候选变换和审阅图保留在独立的initial_gradient_descent记录中。

随后只重试一种步长受控方法：RegularStepGradientDescent，初始步长0.5、最小步长0.005、松弛0.5、每层最多200次。此限制作用于每步，不是全局总位移约束。结果如下，表中“之后”均指**未采用的候选变换**：

| 病灶 | 全量负互信息之前 | 候选之后 | 平移范数（mm） | 工程筛查 |
| --- | ---: | ---: | ---: | --- |
| 10005_L1 | -0.433252 | -0.077393 | 128.682891 | 拒绝 |
| 10029_L2 | -0.303253 | -0.316020 | 0.371285 | 仅供解剖复核 |
| 40158_L1 | -0.203292 | -0.200457 | 2.083735 | 拒绝 |

数值工程筛查要求负互信息改善、固定强度前景的移动视野重叠减少不超过2个百分点。后者是本轮工程报警设置，不是临床可接受阈值；任何工程通过均不直接生成临床接受标记。10005_L1的前景视野重叠由95.59%降至23.73%，原审阅图也可见明显移位，因此拒绝。40158_L1目标坐标视野覆盖虽由98.30%变成100%，全量互信息仍未改善；覆盖比例增加不能推翻拒绝决定，更不能证明原来未采集的组织被恢复。

10029_L2仅满足数值筛查，仍未由临床/解剖标准确认。**三个候选均未应用于正式分析，临床接受数为0，use_for_model均为0。** 没有把头信息恒等变换自动认证为临床对齐，也没有继续扫参直至取得期望结果。

固定参数后复算10005_L1，六个变换参数的最大差异为0，支持本环境这一例数值可复现；可复现不代表方法有效。该重复检查不代表其他硬件或所有病例的复现验证。

审阅图：[10005_L1](../outputs/registration-pilot-20261029/10005_L1_registration_review.png)、[10029_L2](../outputs/registration-pilot-20261029/10029_L2_registration_review.png)、[40158_L1](../outputs/registration-pilot-20261029/40158_L1_registration_review.png)。红色为T1、绿色为FLAIR；同一T1显示网格上的叠加图只用于技术审阅，不构成RN诊断。

## 公开终点核查与决定

2026-10-29重新获取原作者当前Nov2023临床文件，SHA256仍为`00a5c7ad0b78361e694310b125b0023e294f21ab2d46a495c0a9f00552a970bd`，未出现新版本。当前仍为160个病灶、35条数值型RN时间、125条未知、0条已核实阴性、0条已核实事件无发生随访截止。54个基线掩膜候选仍未启用建模。

重新查阅2023年数据描述论文、2026年RN-D3全文及其公开代码树。后者描述的是RN检测/分割与诊断区分，不能把其中的诊断特异性病例直接当作本研究治疗前风险预测的无事件随访对照。所查代码树`c4619bab9f27c102a25341ed838dea49fe9ac0c5`有22个文件，仅观察到含patient001/patient002的合成示例registry，未取得与MOLAB逐病灶对应的真实临床标签表。

PMC的DOCX附录链接呈现访问验证；已阅读出版社正文，但未取得附录字节，附录内容未核查。这个限制已明确保留，不能声称附录不含所需标签，也不能声称全网不存在其他公开标签。未联系作者或请求非公开病历。

**原风险模型当前不能识别所需事件/无事件随访，不能训练或报告AUC。** 无须要求所有160条原始记录均完整；若将来存在有完整公开证据、符合时间索引的可分析子队列，可重新评估。但不能把当前空白、死亡、晚期MRI、组织坏死掩膜或模型输出补成阴性真值。当前停止扩大全队列自动配准，优先解决公开终点来源或核查完整公开标签队列，避免继续影像处理却无法回答原研究问题。

## 交付与重现

- Notebook09：`notebooks/09_registration_pilot_and_endpoint_gate.ipynb`，5个代码单元已在进程内ipykernel执行，无错误；回执独立保存为`reports/kernel_execution_09.json`。
- 当前试验及首轮失败CSV、两份JSON、六个策略/病例组合、候选变换和审阅图均保留。
- `RN_Registration_Pilot_and_Model_Gate.xlsx`含Summary、Trials、Sources三页，公式汇总已核对并渲染检查。
- 32项测试通过，新增验证RAS/LPS物理坐标、数组轴顺序、重采样变换方向，以及坐标视野比例改善不能覆盖互信息变差的拒绝规则。没有独立内核服务器或浏览器前端验证。

```bash
python -m pip install -r requirements.txt
python scripts/restore_sources.py
# 恢复归档01/15到dist/restored_mri；或用既有源恢复脚本下载所需成员。
python scripts/check_endpoint_gate.py --refresh
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_09.json notebooks/09_registration_pilot_and_endpoint_gate.ipynb
python scripts/make_pilot_workbook_input.py
python -m unittest discover -s tests -v
```

刷新临床文件若SHA256改变，会另存新字节，原文件不覆盖；旧结果不能自动视为适用于新版本。Excel由artifact-tool Node构建器导出，Python输入脚本本身不创建Excel。复算配准需793张源DICOM，只有Git中的索引或变换文件不能代替影像字节。

方法来源：[SimpleITK配准概述](https://simpleitk.readthedocs.io/en/main/registrationOverview.html)、[变换与重采样](https://insightsoftwareconsortium.github.io/SimpleITK-Notebooks/Python_html/21_Transforms_and_Resampling.html)。终点核查：[原作者临床文件](https://dw.molab.es/indices/bm1/OpenBTAI_METS_ClinicalData_Nov2023.xlsx)、[2023描述论文](https://www.nature.com/articles/s41597-023-02123-0)、[2026 RN-D3论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC13490108/)、[所查RN-D3代码树](https://github.com/chamseddine-lab/rn-d3/tree/c4619bab9f27c102a25341ed838dea49fe9ac0c5)。
