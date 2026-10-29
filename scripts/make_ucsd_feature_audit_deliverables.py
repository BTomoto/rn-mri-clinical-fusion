"""Produce the step12 report, availability figure and typed workbook inputs."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/ucsd_feature_audit'
s=json.loads((R/'clinical_summary.json').read_text());access=json.loads((R/'mri_access_receipt.json').read_text())
inv=json.loads((R/'mri_inventory_receipt.json').read_text())
raw=pd.read_csv(ROOT/'data/processed/ucsd_clinical_all_fields_raw.csv')
c=pd.read_csv(ROOT/'data/processed/ucsd_clinical_feature_candidates.csv')
a=pd.read_csv(R/'clinical_field_audit.csv');issues=pd.read_csv(R/'case_issues.csv')
folders=pd.read_csv(R/'mri_folder_inventory_1221.csv');files=pd.read_csv(R/'mri_sample_file_inventory.csv')
sample=pd.read_csv(R/'mri_sample_request.csv')
sample['priority']=sample.ID.isin(['UCSD-PTGBM-0001_01','UCSD-PTGBM-0003_01']).map({True:1,False:2})
sample['download_package_assignment']=sample.ID.isin(folders.ID).map({True:'1221: directory ID verified',False:'not in 1221 inventory; 1019 case assignment unverified'})
sample['requested_sequences']='T1pre, T1post, T2, FLAIR, ADC_vendor, BraTS_tumor_seg; source label legend; perfusion optional'
sample.to_csv(R/'mri_sample_request.csv',index=False)
access['conclusion']='Public metadata and transfer parameters accessible. Main-package listing timed out; test-package 59-case folder inventory and two 23-entry file lists obtained. File entries are symbolic links with unverified targets; no NIfTI downloaded, header/pixel/ROI quality not verified. HTTP gateway not configured.'
(R/'mri_access_receipt.json').write_text(json.dumps(access,indent=2))
inventory_checks=dict(checked_folders=59,source_patient_ids=42,tumor_timepoints=49,treatment_change_timepoints=10,
    sample_case_file_entries=int(len(files)),sample_entries_symbolic_links=int(files.type.eq('symbolic_link').sum()),
    sample_entries_known_byte_size=int(files['size'].notna().sum()),
    symlink_targets_resolved=False,source_NIfTI_bytes_downloaded=0,header_geometry_verified=False,pixel_quality_verified=False)
(R/'mri_inventory_checks.json').write_text(json.dumps(inventory_checks,indent=2))
out=ROOT/'outputs/ucsd-feature-audit-20261029';out.mkdir(parents=True,exist_ok=True)
labels=['Age','Sex','Other prior treatment','Initial-event interval*','MGMT (raw)','IDH (raw)','1p19q (raw)','ATRX (raw)','MGMT + IDH (raw)','Last-radiation interval*']
counts=[243,243,243,197,149,168,112,114,135,117]
fig,ax=plt.subplots(figsize=(10,6))
fig.subplots_adjust(left=.30,right=.96,bottom=.18,top=.90)
bars=ax.barh(labels[::-1],counts[::-1],color=['#476D89' if '*' not in x else '#A47945' for x in labels[::-1]])
ax.axvline(243,color='#777777',linestyle='--',linewidth=1)
for bar,n in zip(bars,counts[::-1]):ax.text(n+2,bar.get_y()+bar.get_height()/2,f'{n}/243',va='center',fontsize=9)
ax.set(xlim=(0,285),xlabel='Scanning timepoints with recorded / temporally admissible data',title='Clinical feature availability before modeling')
ax.spines[['top','right']].set_visible(False)
fig.text(.02,.035,'* Strictly before scan and excluding detected temporal conflicts. Availability is not model eligibility.',fontsize=8)
fig.savefig(out/'clinical_feature_availability.png',dpi=180,bbox_inches='tight');plt.close(fig)
def typed(d):return dict(headers=d.columns.tolist(),rows=json.loads(d.to_json(orient='values')))
payload=dict(summary=s,access=access,inventory=inv,inventory_checks=inventory_checks,
             fields=typed(a),raw=typed(raw),candidates=typed(c),issues=typed(issues),sample=typed(sample))
(ROOT/'reports/ucsd_feature_workbook_input.json').write_text(json.dumps(payload,ensure_ascii=False))
text=f'''# 第12步：完整临床变量与MRI可行性核查

2026-10-29。用户已批准本步核查。**36个临床字段、双ID映射及公开MRI访问核查完成；未拟合新模型。MRI取得目录/文件名证据，但没有取得NIfTI像素数据，不能声称完成影像质控或ROI验证。**

## 关键更正：上轮验证指标暂不能作为最终结果

临床v3仍有一处双ID交叉：

| 临床扫描ID | BraTS扫描ID | 上轮验证折 |
| --- | --- | ---: |
| UCSD-PTGBM-0036_01 | BraTS-GLI-02289-100 | 5 |
| UCSD-PTGBM-0036_02 | BraTS-GLI-02289-101 | 5 |
| UCSD-PTGBM-0038_01 | BraTS-GLI-02291-100 | 4 |
| UCSD-PTGBM-0038_02 | BraTS-GLI-02291-101 | 4 |
| UCSD-PTGBM-0038_03 | BraTS-GLI-02289-102 | 4 |

相同BraTS患者前缀02289跨第4、5折。此前“患者不重叠”的检查只对临床ID成立，不能排除另一ID体系下的潜在重复患者。不能自行断定0038_03一定应改为0036_03，也不能以生成新编号代替证据。因此上轮AUC=0.5755、区间、校准及系数保留为**待重新验证的历史结果**，不作为后续主结果。

生成双ID连通分组177组，仅用于保守阻断分组交叉，不是真实患者数修订。源表仍为178名患者。本步未重训；下一步可预先隔离2个源患者的5次扫描，保留238次扫描、176个源患者，再进行新的分组验证。5条均属推导肿瘤类，隔离后为187次肿瘤、51次治疗改变；该隔离建议与性能高低无关。

## 完整临床字段的可用程度

固定原始v3 SHA256：`{s['source_sha256']}`。本轮重新读取官网文件的SHA256相同：{access['clinical_workbook_current_sha256']==s['source_sha256']}。原始XLSX未改写，完整36列导出CSV；字段说明、未知及条件性空白单独记录。扫描时间点不是独立患者样本量。

| 资料 | 有记录/严格可用的扫描数 | 说明 |
| --- | ---: | --- |
| 年龄、性别 | 各243 | 扫描时已知 |
| 其他扫描前治疗 | 243 | 来源明确写prior to scan，但只是宽泛Yes/No，治疗异质性高 |
| 初始事件间隔 | 197 | 198条数值中1条同日；混合手术/治疗/诊断，不命名为距手术时间 |
| MGMT | 149 | 94条缺失；1个源患者3条结果冲突 |
| IDH | 168 | 75条缺失；1个源患者2条结果冲突 |
| 1p19q / ATRX | 112 / 114 | 缺失多，分子检测均无检测时间戳 |
| MGMT与IDH同时有记录 | 135 | 100个源患者，106次肿瘤、29次治疗改变；尚未剔除分子冲突 |
| 最后放疗间隔 | 117 | 严格扫描前且隔离日期方向/顺序冲突；非全队列变量 |
| 首次化疗间隔 | 122 | 已有数值均为扫描前，但其他病例不能自动视为未化疗 |

36字段全部有逐列审阅结论。年龄、性别与其他扫描前治疗为直接候选；初始事件间隔为有缺失的候选。治疗过程和分子指标均列为条件候选，需冻结规则后才能入模。没有因为单变量结果更好就筛入某个变量。

原始记录中，Radiation=Yes有141次、No有102次，不能把本队列全称为“放疗后”样本；研究定位仍为治疗后。Grade 2/3共3次和Grade 5诊断文本异常均保留，纯GBM/Grade 4限制应作为预先指定的敏感性分析，不能事后按模型效果删例。

## 时间和一致性问题

记录到33条问题标记（同一次扫描可能出现多个问题），其中7条未来治疗偏移、7条同日先后不明、2条首次/最后放疗顺序冲突、5条双ID交叉映射、5条患者内分子结果冲突、2条Surgery=No与GTR不一致等。

例如0126_01的“扫描前最后手术”偏移为+35天；0145_01的“扫描前最后放疗”是+8天；0024_01、0133_02、0167_01和0167_02的“扫描前Avastin”日期为正。未翻转符号、改成0或当作扫描前暴露。0001_01首次放疗−591、最后放疗−914，顺序不成立，整体隔离放疗间隔。偏移0的事件也不自动认为发生在扫描之前。

随访、死亡、OS及PFS四类字段仅作审计，排除出候选预测数据。分子值不从后续扫描回填到较早扫描；MGMT冲突源患者0038及IDH冲突源患者0145的相应清洗候选值隔离为未知。源表的No、Unknown和空白不合并为0。条件性空白（例如last surgery if different）不等同没有手术。

## MRI获取：已经确认到哪一层

| 证据 | 已完成内容 | 尚未确认 |
| --- | --- | --- |
| 官方公开入口 | 两个链接均取得公开下载授权；无需用户账户密码 | 不等于下载成功 |
| 包元数据 | 主包136人/184时间点、另一包42人/59时间点；4047/1322条为源方报告文件数 | 主包目录本环境请求超时 |
| 测试包目录 | 实际列出59个病例文件夹，对应42个临床源患者；49次肿瘤、10次治疗改变 | 目录名匹配不等于解决BraTS交叉映射 |
| 两例文件名 | 0001_01（临床PsP）与0003_01（肿瘤）各23个条目；可见T1pre/post、T2、FLAIR、ADC、ASL、CBV等命名 | **46个条目均为symbolic_link，大小未知，目标能否解析未证实** |
| 实际影像检查 | 下载数0、NIfTI头/仿射/像素质控0 | 不能声称配准、覆盖或ROI可用 |

Faspex网页公开配置没有HTTP网关，本环境也没有Aspera传输客户端；对服务器公布的33001端口单次TCP连接返回OSError，具体网络原因未判定。这些是本环境的访问限制，不表示公开数据不存在。下载参数可取得，实际传输和符号链接解析仍须验证。服务器API的`total_bytes`仅报告117669/300201等与官网GB规模不符的值，没有将其当作真实MRI字节数。

已生成6例技术样本清单，优先取得测试包内0001_01和0003_01的T1pre、T1post、T2、FLAIR、ADC_vendor、普通BraTS分割及标签说明；其余4例覆盖其他治疗改变亚型。样本按技术目的选择，不能用作模型效果验证样本。可通过[官方集合页](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/)进入IBM Aspera下载；无需向本项目提供个人账号密码。当前尚未证明本环境可以独立完成传输。

## ROI与发表定位

数据论文说明，细胞性肿瘤TCT/ECT/NECT参考标注利用了临床/病理及前后扫描信息。因此其掩膜、体积、空非空和文件存在性均不得作为本任务输入。普通BraTS分割是否对诊断标签盲法、两组是否均有同等可用的异常区域，仍需验证。当前文件名含分割不等于每组掩膜非空或标签编码已核实。影像也参与了部分参考诊断形成，可能存在参考标准的纳入偏倚；去掉参考掩膜不能自动消除这一限制，也不能用初次手术/活检字段推断当前时间点有独立病理确诊。

拟采用仅基于当前扫描FLAIR/T1增强的统一异常区域流程，处理手术腔和空ROI，并核查自动分割模型是否曾使用本队列训练。未取得像素及标签说明前，只能称为拟定方案。MRI、临床与融合模型将来必须在相同病例和分组上比较，不能把全临床队列与MRI子集直接比较当作增量价值。

该数据来源已有相关灌注/深度学习鉴别研究（10.1093/noajnl/vdaf219）。后续贡献需围绕可复现的简化流程、临床信息的增量价值和可靠验证展开，不能只以换算法或加入MRI声称创新；本步未评估其最终可发表性。

## 本步结论、受限原因与下一步计划

临床字段审计成功，现有信息确实超过年龄和性别；但全部字段同时入模会混入未来信息、身份不确定性和大量缺失。MRI公开入口及部分目录/文件名核查成功，像素层面未完成的直接原因是当前缺少可用传输路径，并非图像质量已判不合格。另有标签与ID映射来源限制尚未关闭。

建议下一步先隔离5条双ID冲突扫描，冻结年龄、性别、初始事件间隔和其他扫描前治疗等少量临床候选；在训练折内制定缺失处理规则，重跑基础对照和扩展临床模型。分子指标仅在明确冲突/时点规则后做次要分析。MRI先取得上述2例技术样本，验证链接解析、几何和ROI，再决定是否扩至6例及全队列。**本步未执行这些建模或像素分析，等待用户再次批准。**

## 文件与复现

`notebooks/12_ucsd_clinical_and_mri_feasibility.ipynb`记录本步核查；`reports/kernel_execution_12.json`保存实际内核执行收据。Excel含Summary、Fields、Clinical_raw、Candidates、Issues、MRI六页，保留全部原始字段及清洗候选，修改Excel不会自动训练模型。完整问题和访问收据在`reports/ucsd_feature_audit/`。源数据、代码和结果保存到既有仓库，临时访问令牌未入库。

```bash
python scripts/audit_ucsd_clinical_features.py
python scripts/audit_ucsd_mri_access.py                 # 读取已保存访问收据
python scripts/audit_ucsd_mri_inventory.py              # 读取已保存目录收据
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_12.json notebooks/12_ucsd_clinical_and_mri_feasibility.ipynb
python scripts/make_ucsd_feature_audit_deliverables.py
```

仅在需要重新联网核查时给MRI脚本加`--refresh`；响应可能随时间变化。本步41项自动检查通过；Notebook的5个代码单元实际执行成功、0错误。导出的Excel全部243条原始记录、243条候选记录、36字段及33条问题标记已逐行核对，六页已渲染审阅，公式缓存与Python一致；保存后核验见`reports/ucsd_feature_audit/artifact_verification.json`。未测试原生Excel应用程序或浏览器Jupyter前端。Excel用artifact-tool构建器生成。来源：[TCIA](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/)、[描述论文](https://doi.org/10.1038/s41597-025-06499-z)、[相关原始研究](https://pubmed.ncbi.nlm.nih.gov/41497450/)、[IBM下载API说明](https://www.ibm.com/docs/en/aspera-faspex/5.0.x?topic=packages-downloading-package-connect)。
'''
(ROOT/'reports/ucsd_clinical_mri_feasibility_step12_20261029.md').write_text(text)
print('Prepared step12 report, figure and workbook input')
