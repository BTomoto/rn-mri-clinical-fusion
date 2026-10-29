"""Prepare typed Excel input and a concise report from actual download/QC receipts."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
base = ROOT/'reports/ucsd_mri_mirror'
j = json.loads((base/'sample_qc_receipt.json').read_text())
s = j['summary']
downloads = json.loads((base/'download_receipt.json').read_text())['files']
lookup = {(r['ID'], r['sequence']): r for r in downloads}
rows = []
for r in j['files']:
    d = lookup[(r['ID'], r['sequence'])]
    rows.append([r['ID'], r['sequence'], r.get('bytes'), r['decoded'],
                 r['release_digest_matches'], 'x'.join(map(str, r.get('shape', []))),
                 r.get('spatial_units'), r.get('stored_dtype'), r['technical_pass'],
                 r['relative_grid_to_FLAIR']['status'], r.get('minimum'), r.get('maximum'),
                 '; '.join(r['issues']), json.dumps(r.get('observed_labels')),
                 r.get('sha256'), d['url'], r['relative_path']])
headers = ['ID', 'sequence', 'bytes', 'decoded', 'release_digest_matches', 'shape',
           'spatial_units', 'stored_dtype', 'physical_QC_pass', 'relative_grid_status',
           'minimum', 'maximum', 'issues', 'observed_label_codes', 'sha256', 'download_URL', 'local_path']
coverage = pd.read_csv(base/'clinical_mirror_sequence_coverage.csv')
out = dict(summary=s, files=dict(headers=headers, rows=rows), coverage=dict(
    headers=coverage.columns.tolist(), rows=coverage.astype(object).where(coverage.notna(), None).values.tolist()))
(ROOT/'reports/ucsd_mirror_workbook_input.json').write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
report = f'''# 第15步：替代HTTPS路线取得真实MRI，完成两例技术验证

2026-10-29（北京时间）。用户批准采用非官方公开下载途径，不要求额外考证原始来源。本步完成普通GitHub Release HTTPS下载及实际体素检查，**无需用户手动下载或安装Aspera**。

## 本步结果

| 项目 | 实际结果 |
| --- | --- |
| 固定技术病例 | 0002_01（治疗改变）、0005_01（推导肿瘤标签） |
| 实际完整下载 | {s['successful_download_files']}份影像，共{s['downloaded_image_bytes']:,}字节（约14.25 MB） |
| 完整体素解码、gzip CRC、镜像SHA256一致 | 12/12 |
| 病例及BraTS两个字段连接 | 两例均一致，沿用现有标签 |
| 形状 | 所有文件256×256×256 |
| 非有限体素 | 所有文件0 |
| 原生相对网格一致 | {s['relative_native_grid_matches']}/12 |
| 空间单位unknown | {s['unknown_spatial_unit_files']}/12 |
| 预设物理尺度质控通过 | {s['technical_pass_image_files']}/12，保留unknown单位问题 |
| 新MRI模型或预测性能 | 未拟合、未估计 |

每例均取得FLAIR、T1平扫、T1增强、T2、ADC_vendor及普通BraTS分割。镜像别名`run-pre_T1w`、`run-post_T1w`、`T2w`分别对应本项目T1pre、T1post、T2，原文件名及内容保持不变。实际文件存放于`data/samples/ucsd_mirror/`，均小于2 MB，可随本项目保存；它们不属于旧OpenBTAI队列。前一步0001_01/0003_01缺文件的记录作为历史保留，当前换用固定的新样本。

## 可以观察到什么

已生成实际FLAIR三平面图、五序列同层图，以及普通BraTS数值标签轮廓叠加。切片由FLAIR非零包围盒中点确定，不按类别、分割大小或模型效果选图。技术预览显示可识别的脑部图像与可见源分割轮廓；仅代表所展示切面，未接受临床解剖配准或重新诊断。两例普通分割均非空：0002_01观察数值0/1/2/3/4，0005_01为0/2/3/4；这些数值没有被解释为具体组织，也未变成体积或预测特征。

Notebook15实际使用进程内Jupyter/ipykernel执行5个代码单元、0错误；三组PNG由真实文件生成并检查。全项目61项测试通过，其中新增4项验证文件别名、病例错配、目录覆盖不等于下载及unknown单位不被自动补成mm。软件测试中的临时小数组不是本步取得的研究图像。独立内核服务器/浏览器前端未验证。

## 未通过项目及原因

下载和像素读取已成功，当前限制来自镜像文件本身的记录形式：

1. **未声明空间单位**。头部sform_code=1、qform_code=0，原生步长为1/1/1，但空间单位unknown，因此不能直接写成1 mm或计算mL体积。保留第14步预设物理尺度检查失败，不自动改头或降标准。
2. **强度仅为8位**。10份强度图均为uint8、缩放1/0、范围0–255。没有据此证明它们与原始定量图等价。ADC当前不能套用原始物理ADC阈值；T1/FLAIR也要按镜像派生图像解释。来源考证不是本步前提，但实际数值尺度必须影响分析方法。
3. **统一预测ROI仍未建立**。普通BraTS掩膜只作技术叠加；TCT/ECT/NECT参考掩膜未下载。当前无标签盲于结局的统一预测ROI方案，也未用掩膜空/非空推断结局。

作为补充的相对网格检查，只比较相同shape、原生仿射与form/单位字段，12份均匹配；它支持同体素索引的技术叠加，不等于毫米尺度或临床配准通过。详细说明见`ucsd_mri_mirror/observed_header_notes.md`。

## 扩大研究的数据基础

镜像列出184次扫描的FLAIR及相应六序列。在已有238次扫描/176名源患者内，隔离既有ID冲突后，目录显示{s['listed_all_six_remaining_timepoints']}次扫描、{s['listed_all_six_remaining_patients']}名源患者具备六项，含{s['listed_all_six_tumor_timepoints']}次肿瘤、{s['listed_all_six_treatment_change_timepoints']}次治疗改变。这是**目录覆盖候选数**，不是182份已下载或已质控的影像。当前实际只取得2例12文件。其余临床病例保留在238行覆盖表中，不因无影像而从临床研究中消失。

第13步临床队列、逐例预测、Excel、指标与模型代码没有改变，没有重训临床模型。未来MRI增量比较须在实际共同病例上重跑相同临床对照，不能将不同人群的AUC相减。

## 下一步计划

本步证明无需用户手动下载即可取得真实影像，替代下载路线可继续使用。建议下一阶段先扩大至少量（例如6例）技术试验，检查8位镜像在更多病例中的一致性，并固定两类统一的当前扫描ROI方案；之后再决定是否开展基于派生图像的无单位强度/纹理分析。物理体积和定量ADC另需解决尺度问题。没有证据时不把步长1假定成1 mm，也不承诺MRI一定提高效果。

本步完成，按用户要求等待下一阶段批准；用户无需下载文件或安装软件。

## 已整理文件与复现

- `outputs/ucsd-mri-mirror-20261029/UCSD_MRI_Mirror_Samples.xlsx`：Summary、Files（12份实际文件）及Coverage（238行临床覆盖）。MRI体素单独存储，不塞进Excel。
- `notebooks/15_ucsd_mri_mirror_samples.ipynb`：实际执行结果及真实图像。
- `reports/ucsd_mri_mirror/`：下载回执、病例映射、覆盖CSV、逐文件QC及完整JSON。
- `data/metadata/ucsd_mirror_asset_inventory.csv`：镜像相关六序列清单；`data/raw/reference/ucsd_mirror_participants.tsv`为原样下载的镜像元数据，未替代临床源表。
- `data/samples/ucsd_mirror/`：12份实际镜像NIfTI。

```bash
python scripts/download_ucsd_mirror_samples.py --refresh-inventory
python scripts/run_notebooks_kernel.py --report reports/kernel_execution_15.json notebooks/15_ucsd_mri_mirror_samples.ipynb
python scripts/make_ucsd_mirror_deliverables.py
python -m unittest discover -s tests -v
```

完整文件存在且哈希一致时复用，不重复传输。重新下载时仍按已固定两例，不自动扩大。Excel由`scripts/build_ucsd_mirror_workbook.mjs`通过artifact-tool生成，需设置RN_PROJECT_ROOT。下载地址、SHA256与大小逐项保存；没有要求或宣称与TCIA原文件字节一致。遵循原数据CC BY 4.0归属：UCSD-PTGBM，DOI 10.7937/fwv2-dt74，描述论文DOI 10.1038/s41597-025-06499-z；镜像整理者`data-nih/tcia`，地址https://github.com/data-nih/tcia/releases。
'''
(ROOT/'reports/ucsd_mri_mirror_step15_20261029.md').write_text(report)
print('Prepared actual sample workbook input and Stage15 report')
