"""Build report, workbook input and a static notebook figure attachment from real results."""
from pathlib import Path
import base64,json
import pandas as pd
import nbformat
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/ucsd_clinical_revalidation'
s=json.loads((R/'metrics.json').read_text());mri=json.loads((R/'mri_sample_transfer_retry.json').read_text())
oof=pd.read_csv(ROOT/'data/processed/ucsd_clinical_revalidated_oof.csv')
secondary=pd.read_csv(R/'complete_interval_sensitivity_oof.csv')
excluded=pd.read_csv(R/'excluded_identity_conflicts.csv')
folds=json.loads((R/'fold_audit.json').read_text())
params=pd.DataFrame([dict(fold=f['fold'],train_age_mean=f['models']['M1']['parameters']['age_mean'],
                          train_log_interval_impute_median=f['models']['M1']['parameters']['log_interval_impute_median'],
                          train_log_interval_mean_after_fill=f['models']['M1']['parameters']['log_interval_mean_after_imputation'],
                          train_log_interval_sd_after_fill=f['models']['M1']['parameters']['log_interval_sd_after_imputation']) for f in folds])
def typed(d):return dict(headers=d.columns.tolist(),rows=json.loads(d.to_json(orient='values')))
payload=dict(summary=s,mri=mri,oof=typed(oof),secondary=typed(secondary),excluded=typed(excluded),
             fold_metrics=typed(pd.read_csv(R/'fold_metrics.csv')),preprocessing=typed(params))
(ROOT/'reports/ucsd_revalidation_workbook_input.json').write_text(json.dumps(payload,ensure_ascii=False))
nbpath=ROOT/'notebooks/13_ucsd_clinical_revalidation.ipynb'
if nbpath.exists():
    nb=nbformat.read(nbpath,as_version=4)
    figure=ROOT/'outputs/ucsd-clinical-revalidation-20261029/clinical_revalidation_comparison.png'
    for cell in nb.cells:
        if cell.cell_type=='markdown' and cell.metadata.get('plot_attachment'):
            cell.attachments={'clinical.png':{'image/png':base64.b64encode(figure.read_bytes()).decode()}}
    nbformat.write(nb,nbpath)
ci=s['patient_cluster_bootstrap_95ci'];metrics=s['metrics'];diff=s['paired_differences_M1_minus_M0'];sec=s['secondary_complete_interval']
lines=[]
for name,label in [('M0','M0：年龄＋性别'),('M1','M1：扩展临床'),('prior','训练折比例对照')]:
    m=metrics[name]
    interval=f"{ci[name]['roc_auc']['lower']:.3f}–{ci[name]['roc_auc']['upper']:.3f}" if name in ci else '未计算'
    lines.append(f"| {label} | {m['roc_auc']:.4f} | {interval} | {m['brier']:.4f} | {m['ap_treatment_change']:.4f} | {m['specificity_treatment_change']:.2%} |")
report=f'''# 第13步：ID隔离后的临床模型重验与扩展

2026-10-29。用户批准继续后，先写入固定方案，再拟合模型。**已完成238次扫描/176名源患者的临床重验：M1 AUC为0.679，M0为0.612；点估计改善，但成对差值区间跨0，尚未确证增益。MRI指定文件的下载参数可取得，实际传输未启动，仍无像素/ROI结果。**

## 队列、标签和验证更正

按第12步已识别的双ID问题，隔离0036_01、0036_02、0038_01、0038_02、0038_03五次扫描，不修改编号或标签。保留238次扫描、176名临床源患者，187次肿瘤与51次治疗相关改变。重新建立5折分组，临床ID和BraTS患者前缀均无训练/验证交叉；每次扫描恰有一个折外概率。11名跨类别患者的不同扫描仍保留同折。

第11步0.5755的结果保留为未解决双ID交叉的历史记录；本步基础模型0.6124同时受人群隔离和重新分折影响，不能把两者差值解释为变量或算法改善。只有本步相同病例/折上的M1对M0比较用于评价临床增量。

研究仍是当前扫描状态的探索性鉴别，不是未来RN风险预测。51条治疗改变来自明细，187条保留肿瘤标签来自官方完整分组的补集推导；非逐例病理金标准。没有重新判定真实患者身份或病理类别。混合组织学、源文本异常及影像参与参考诊断的限制仍在。

## 本步模型纳入了什么

| 信息 | M0 | M1 | 处理 |
| --- | --- | --- | --- |
| 扫描时年龄 | 是 | 是 | 训练折内标准化 |
| 出生性别 | 是 | 是 | Male=1，Female=0 |
| 初始事件间隔 | 否 | 是 | 严格扫描前，log1p；训练折中位数填补后标准化 |
| 其他扫描前治疗 | 否 | 是 | 来源明确prior to scan的Yes/No，异质性宽泛 |
| 初始事件间隔缺失标记 | 否 | 是 | 记录缺失状态，非新增生物学指标 |

因此M1含4项临床变量、5个非截距系数。时间字段混合最初手术/治疗/诊断，不能称为距手术天数。MGMT、IDH等仍无可靠检测时点且有冲突，本步未纳入。未来随访、死亡、OS/PFS、诊断亚型及MRI参考掩膜均不作为输入。

固定L2 Logistic、C=1、lbfgs、max_iter=2000；5折StratifiedGroupKFold、种子20261029。没有调参、模型搜索、类别权重或阈值优化。缺失间隔共46次，严格有效192次；插补和缩放从不使用验证折。对照仅使用相应训练折的肿瘤比例。

## 主分析：同病例同折的OOF结果

| 模型 | ROC AUC | 患者簇95%区间 | Brier（越低越好） | 治疗改变AP | 特异度，阈值0.5 |
| --- | ---: | --- | ---: | ---: | ---: |
{chr(10).join(lines)}

M1−M0的AUC差为{diff['roc_auc']:.4f}，95%区间{ci['M1_minus_M0']['roc_auc']['lower']:.4f}至{ci['M1_minus_M0']['roc_auc']['upper']:.4f}；Brier差为{diff['brier']:.4f}，95%区间{ci['M1_minus_M0']['brier']['lower']:.4f}至{ci['M1_minus_M0']['brier']['upper']:.4f}。两个差值区间均跨0，因此结论限于改善趋势，不宣称已经证明M1优于M0。

区间来自2000次患者整簇重采样，M0/M1使用同一抽样，概率固定为本次OOF结果。它不涵盖全部重新训练/划分的不确定性，不是外部验证。比例对照OOF AUC略偏离0.5来自各折训练比例不同，不代表恒定预测器有实用排序能力。

固定0.5阈值的M1混淆矩阵：

| 真实状态 | 预测治疗改变 | 预测肿瘤 |
| --- | ---: | ---: |
| 治疗相关改变 | 5 | 46 |
| 残余/复发肿瘤 | 4 | 183 |

肿瘤敏感度{metrics['M1']['sensitivity_tumor']:.2%}，治疗改变特异度{metrics['M1']['specificity_treatment_change']:.2%}，平衡准确率{metrics['M1']['balanced_accuracy']:.2%}。总体准确率{metrics['M1']['accuracy']:.2%}，但全部判肿瘤即可达到78.57%，不能据准确率声称模型有效。0.5只是一项固定阈值结果；本步没有在验证数据上挑选更有利的阈值。校准图仅为5分位区间的描述性图，不证明临床可用。

## 完整时间资料敏感性分析

预先指定的次要分析纳入192次扫描、142名源患者（145次肿瘤、47次治疗改变），对该子集重新固定5折。M0 AUC={sec['metrics']['M0']['roc_auc']:.4f}、M1={sec['metrics']['M1']['roc_auc']:.4f}；Brier分别为{sec['metrics']['M0']['brier']:.4f}和{sec['metrics']['M1']['brier']:.4f}。次要分析未计算区间，不能视为独立确证。

主分析缺失的46次中42次为肿瘤、4次为治疗改变，缺失模式与类别相关，可能反映回顾性记录差异。完整资料子集中扩展模型仍有较高点估计，但不能据此证明已经消除缺失偏倚；子集病例与折均不同，也不能把其0.623直接与主分析0.679作模型优劣比较。未按次要结果替换主分析。

## MRI实际文件重试

重新通过官方公开链接取得授权，明确请求0001_01和0003_01两份FLAIR文件的下载参数（HTTP {mri.get('download_parameter_http_status','未取得')}）。服务器返回两份指定文件的传输路径，**这仍然不是取得NIfTI文件或解析了符号链接目标**。

本环境无Aspera客户端，HTTP网关为空；对服务器公布的144.30.235.113:33001连接返回OSError/errno=101（网络不可达）。实际传输未启动，文件数0、字节数0，不能计算头信息、仿射、像素覆盖或ROI特征。HTTP备用传输与HTTP网关不是同一机制；本环境尚未验证服务端是否支持客户端备用传输。

已准备`MRI_SAMPLE_DOWNLOAD_CN.md`，说明在本地从官方测试包取得两例最小样本的步骤及文件名。无需提供个人账号密码。先取得少量真实文件再做质控，可避免无目的下载全队列。临床分析没有因MRI访问受限而停住，但后续融合比较仍必须在共同的MRI可用病例上重跑临床对照。

## 本步受限原因与下一步

程序、身份隔离和折内预处理检查成功；扩展变量提供了有限鉴别信号，但增益不确定，固定阈值对治疗改变识别仍不足。限制包括单中心、小对照组、重复扫描、推导标签、混合初始事件字段、宽泛的其他治疗变量及记录缺失模式。全队列拟合参数只作重建/描述，不作独立危险因素或因果推断。

本步已完成获批的临床重验和扩展比较。下一步优先取得两例实际MRI并做解码、网格、链接解析和统一ROI检查；通过后再决定扩大至6例或全队列。MGMT/IDH是否能加入，仍需检测时点与冲突依据。**本步不继续增加算法或训练影像模型，等待用户批准下一阶段。**

## 文件与复现

- `data/processed/ucsd_clinical_revalidated_cohort.csv`、`ucsd_clinical_revalidated_oof.csv`：238条纳入数据与同一病例的M0/M1/对照OOF概率。
- `reports/ucsd_clinical_revalidation/`：隔离清单、两套分组、折内插补参数、敏感性预测、2000次成对差值、指标及MRI重试收据。
- `notebooks/13_ucsd_clinical_revalidation.ipynb`：实际Jupyter/ipykernel执行记录，保留代码、结果和图；未测试浏览器前端或独立内核服务器。
- `outputs/ucsd-clinical-revalidation-20261029/UCSD_Clinical_Revalidation.xlsx`：Summary、OOF、Folds、Sensitivity、Scope五页；逐例误差、Brier和混淆计数有Excel公式，AUC及区间由Python计算。修改Excel不会重训模型。
- 同目录PNG/PDF为真实OOF比较图。

```bash
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_13.json notebooks/13_ucsd_clinical_revalidation.ipynb
python scripts/make_ucsd_revalidation_deliverables.py
python scripts/probe_ucsd_mri_sample_transfer.py        # 默认读取收据，--refresh才联网
python -m unittest discover -s tests -p 'test_ucsd_clinical_revalidation.py' -v
```

固定方案及分析代码SHA256保存在指标JSON。原始公开工作簿和历史输出未覆盖；所有病例可追溯。Excel由artifact-tool构建器生成，本步47项自动测试通过；Notebook实际执行5个代码单元、0错误。Excel的238条主分析及192条次要分析OOF记录、5条隔离记录均逐行核对，五页已渲染审阅；公式输入变化及缓存值与Python一致。保存后校验另见`artifact_verification.json`。来源：[TCIA](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/)、[数据论文](https://doi.org/10.1038/s41597-025-06499-z)、[scikit-learn预处理说明](https://scikit-learn.org/1.8/common_pitfalls.html#data-leakage)。
'''
(ROOT/'reports/ucsd_clinical_revalidation_step13_20261029.md').write_text(report)
print('Prepared step13 report, workbook input and notebook figure attachment')
