"""Package the frozen manuscript data, without downloading MRI or fitting models."""
from pathlib import Path
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile

SOURCE_COMMIT = '73f04f53c42257a7c45a64aaa96066d8dc61660f'
NAME = 'UCSD_Manuscript_Essential_Data_20261030'
FOLDER = 'data_packages/ucsd_manuscript_essential'

PATTERNS = [
    r'^(DATA_LICENSES\.md|requirements.*\.txt|pyproject\.toml)$',
    r'^data/raw/reference/ucsd_(ptgbm_clinical_v3\.xlsx|ptgbm_negative_cases\.xlsx|mirror_participants\.tsv)$',
    r'^data/metadata/(public_label_audit_20261029/downloaded_sources\.json|ucsd_mirror_inventory_receipt\.json)$',
    r'^data/processed/ucsd_(clinical_all_fields_raw|clinical_revalidated_cohort|clinical_image_features|image_features|image_features_eroded|fusion_oof|stability_repeated_oof|stability_single_scan_oof|ptgbm_label_feasibility)\.csv$',
    r'^reports/ucsd_batch_features/(all_clinical_case_status|coverage_by_status_and_label|feature_dictionary|source_manifest|actual_file_QC|normalization_and_texture_diagnostics)\.csv$',
    r'^reports/ucsd_feature_audit/identity_mapping\.csv$',
    r'^reports/ucsd_clinical_revalidation/excluded_identity_conflicts\.csv$',
    r'^reports/ucsd_fusion/(analysis_lock\.json|metrics\.json|cohort_and_fold_manifest\.csv|paired_patient_bootstrap\.csv|fold_audit\.json|paired_comparisons\.csv|calibration_bins\.csv|model_metrics\.csv|full_fit_coefficients\.csv)$',
    r'^reports/ucsd_stability/(analysis_lock\.json|metrics\.json|repeated_fold_manifest\.csv|repeated_metrics\.csv|repeated_paired_differences\.csv|single_scan_fold_manifest\.csv|single_scan_selection\.csv|single_scan_patient_bootstrap\.csv|single_scan_metrics\.csv)$',
    r'^reports/ucsd_(fusion|stability|batch_features)_protocol\.md$',
    r'^src/rn_public/(__init__|ucsd_(fusion|stability|clinical_revalidation|clinical_baseline|batch_features|roi_pilot|mri_mirror|feature_audit|mri_intake|intensity_followup)|remotezip)\.py$',
]

README = '''# 论文必要数据包 / Essential manuscript data

对应论文：Clinical-MRI Feature Fusion for Distinguishing Residual or Recurrent Tumor from Treatment-Related Changes after Glioma Treatment: A Public-Data Internal Validation Study。

版本：2026-10-30；对应 Revision 1。原始文件快照固定在 GitHub 提交 `{commit}`。

## 从哪里开始

主要分析表是 `data/processed/ucsd_clinical_image_features.csv`：182次检查、135名患者，含标签、临床输入和8个MRI特征。`tumor_label=1` 为残留或复发肿瘤，`0` 为治疗相关改变。原始临床资料和派生数据分开保留，CSV采用UTF-8，检查编号和患者编号均沿用公开数据集中的编号。

| 内容 | 路径 | 用途 |
| --- | --- | --- |
| 原始临床工作簿 | `data/raw/reference/ucsd_ptgbm_clinical_v3.xlsx` | 原始243次检查、178名患者；含来源数据字典 |
| 原始治疗相关改变病例清单 | `data/raw/reference/ucsd_ptgbm_negative_cases.xlsx` | 核对51次治疗相关改变检查及来源诊断文字 |
| 镜像参与者元数据 | `data/raw/reference/ucsd_mirror_participants.tsv` | 核对临床与影像编号的对应关系 |
| 全部原始临床字段导出 | `data/processed/ucsd_clinical_all_fields_raw.csv` | 243行、36字段，便于程序读取；这是工作簿的导出表 |
| 临床分析队列 | `data/processed/ucsd_clinical_revalidated_cohort.csv` | 238次检查、176名患者，支持纳入流程和临床覆盖表 |
| 主模型输入 | `data/processed/ucsd_clinical_image_features.csv` | 182次检查、135名患者，141次肿瘤、41次治疗相关改变 |
| MRI特征及边界分析特征 | `data/processed/ucsd_image_features*.csv` | 8个MRI特征的原始提取数值和边界分析数值；属于派生数据 |
| 主分析预测 | `data/processed/ucsd_fusion_oof.csv` | 各模型逐检查折外肿瘤概率、标签、折号和0.5阈值分类 |
| 补充分析预测 | `data/processed/ucsd_stability_*_oof.csv` | 20次分组划分和135次单检查分析 |
| 分组划分、锁定配置和结果 | `reports/ucsd_fusion/`、`reports/ucsd_stability/` | 核对AUC、AP、校准、误差和已保存的bootstrap区间 |
| 纳入与影像文件清单 | `reports/ucsd_batch_features/` | 238次检查的覆盖状态、546个影像文件的地址与哈希、已记录质控 |
| 字段解释 | `DATA_DICTIONARY.csv`、`reports/ucsd_batch_features/feature_dictionary.csv` | 临床编码、标签、概率及MRI特征定义 |
| 核验程序 | `verify_package.py`、`Verify_Essential_Data.ipynb` | 验证完整性、患者分组及关键论文结果 |
| 原分析代码快照 | `src/rn_public/` 和3个protocol文件 | 保存当前数据生成与分析规则；完整研究notebook仍在仓库 `notebooks/18...`、`19...` 和 `20...` |

## 数据范围

本包保留必要的表格级来源数据、MRI特征、分组信息和已保存结果。MRI体素图像及分割文件没有装入压缩包。使用本包可以从原始临床工作簿重建临床变量，并用已提取MRI特征进行模型分析，也可以直接重算折外预测的指标。若要从图像重新提取MRI特征，使用 `reports/ucsd_batch_features/source_manifest.csv` 中546条记录获取对应FLAIR、T1post和BraTS分割文件；该清单同时保存文件地址、字节数和SHA256。包内MRI特征不能替代体素图像进行重新提取。

完整来源临床表只有约0.1 MB，因此保留原工作簿和51例来源清单有助于核对排除记录及纳入流程。公开源表包含的其他字段不会自动进入模型；实际模型变量由 `reports/ucsd_fusion/analysis_lock.json` 确定。标识字段只用于连接及分组。

## 快速核验

解压后进入本目录，使用原分析环境中的Python，或在新环境安装 `requirements_verify.txt` 后运行：

```bash
python verify_package.py
```

也可在Jupyter中打开 `Verify_Essential_Data.ipynb` 并运行全部单元。核验程序读取现有结果、重建临床输入和重新计算指标，不会拟合模型、下载MRI或覆盖原始文件。它检查所有包内文件的SHA256、来源工作簿、临床映射、182次主分析检查、135次单检查、20次重复划分、患者分组和bootstrap百分位区间。

模型拟合及完整图表的notebook：
- https://github.com/BTomoto/rn-mri-clinical-fusion/blob/{commit}/notebooks/18_ucsd_clinical_mri_fusion.ipynb
- https://github.com/BTomoto/rn-mri-clinical-fusion/blob/{commit}/notebooks/19_ucsd_model_stability.ipynb
- https://github.com/BTomoto/rn-mri-clinical-fusion/blob/{commit}/notebooks/20_ucsd_paper_tables_and_figures.ipynb

原分析的完整环境见 `requirements.txt`。重新拟合请使用仓库的完整环境与相应notebook，并另存输出；当前包保持论文结果的固定快照。

## 来源、署名与文件校验

来源：公开UCSD-PTGBM集合，https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/ 。描述论文：Gagnon等，https://doi.org/10.1038/s41597-025-06499-z 。原临床工作簿的来源记录列明CC BY 4.0；来源链接和原始哈希见 `data/metadata/public_label_audit_20261029/downloaded_sources.json`。镜像文件记录见相应清单，数据来源及许可说明见 `DATA_LICENSES.md`。本包没有加入其他研究队列。

`MANIFEST.json` 逐文件记录字节数、SHA256、来源仓库路径、Git blob SHA及数据角色。来源文件均逐字节复制；本次新增内容只有打包说明、字段说明、核验代码和manifest。概率、标签、特征、模型配置及已有统计结果均沿用固定版本。

English note: This compact package contains original public clinical workbooks and derived analysis tables for the Revision 1 manuscript. MRI voxel data are referenced through a 546-file manifest rather than bundled. All source payloads are byte-identical to the pinned repository commit. Run `python verify_package.py` to verify hashes, cohort membership, patient-grouped partitions, clinical reconstruction and saved prediction-based results. No models are fitted by this check.
'''

VERIFY = r'''"""Read-only validation of the essential manuscript data package."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

def check(root):
    root = Path(root).resolve()
    manifest = json.loads((root/'MANIFEST.json').read_text())
    for f in manifest['files']:
        p = root/f['path']
        assert p.stat().st_size == f['bytes'], f['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == f['sha256'], f['path']
    read = lambda name: pd.read_csv(root/name)
    load = lambda name: json.loads((root/name).read_text())
    def close(a, b):
        np.testing.assert_allclose(a, b, rtol=0, atol=1e-10)
    def same_ids(a, b):
        assert not a.ID.duplicated().any() and not b.ID.duplicated().any()
        assert set(a.ID) == set(b.ID)
    def grouped(f):
        assert set(f.validation_fold) == {1,2,3,4,5}
        for ns in ['patient_id', 'brats_patient_id', 'validation_group']:
            assert f.groupby(ns).validation_fold.nunique().eq(1).all(), ns
    def metrics(frame, names, saved):
        y = frame.tumor_label.to_numpy()
        for name in names:
            p = frame[name+'_oof_probability'].to_numpy()
            assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
            actual = dict(roc_auc=roc_auc_score(y,p),
                          ap_treatment_change=average_precision_score(1-y,1-p),
                          brier=brier_score_loss(y,p), log_loss=log_loss(y,p))
            for k,v in actual.items(): close(v,saved[name][k])
            predicted = p>=0.5
            for k,v in dict(tp=((y==1)&predicted).sum(),tn=((y==0)&~predicted).sum(),
                            fp=((y==0)&predicted).sum(),fn=((y==1)&~predicted).sum()).items():
                assert int(v)==saved[name][k], (name,k)
    def intervals(frame, saved):
        assert len(frame)==2000 and frame.draw.nunique()==2000
        for name,v in saved.items():
            close(np.percentile(frame[name],[2.5,97.5]),[v['lower'],v['upper']])

    # Reconstruct labels and clinical inputs from the two original workbooks.
    sys.path.insert(0,str(root/'src'))
    from rn_public.ucsd_clinical_revalidation import prepare_cohort
    clinical, excluded = prepare_cohort(root)
    frozen = read('data/processed/ucsd_clinical_revalidated_cohort.csv')
    for d in [clinical, frozen]: d['initial_event_offset_raw']=d.initial_event_offset_raw.astype(str)
    pd.testing.assert_frame_equal(clinical,frozen)
    assert len(excluded)==5
    d = read('data/processed/ucsd_clinical_image_features.csv')
    assert (len(d), d.patient_id.nunique(), d.validation_group.nunique(), int(d.tumor_label.sum()))==(182,135,135,141)
    d['initial_event_offset_raw']=d.initial_event_offset_raw.astype(str)
    pd.testing.assert_frame_equal(d[clinical.columns],clinical[clinical.ID.isin(d.ID)].reset_index(drop=True))
    lock = load('reports/ucsd_fusion/analysis_lock.json')
    for p,digest in lock['input_sha256'].items(): assert hashlib.sha256((root/p).read_bytes()).hexdigest()==digest
    for fn in ['ucsd_image_features.csv','ucsd_image_features_eroded.csv']:
        f = read('data/processed/'+fn); same_ids(d,f)
        assert np.isfinite(f[lock['model_features']['MRI']].to_numpy()).all()
    original = read('data/processed/ucsd_image_features.csv')
    pd.testing.assert_frame_equal(d[['ID',*lock['model_features']['MRI']]],original)
    assert d.initial_event_missing.sum()==36
    assert d.initial_event_missing.eq(d.log_initial_event_days.isna().astype(int)).all()
    pred = read('data/processed/ucsd_fusion_oof.csv')
    fold = read('reports/ucsd_fusion/cohort_and_fold_manifest.csv')
    same_ids(d,pred); grouped(pred)
    pd.testing.assert_frame_equal(pred[fold.columns],fold)
    close(d.tumor_label,pred.tumor_label)
    main = load('reports/ucsd_fusion/metrics.json')
    metrics(pred,['M0','M1','MRI','Fusion','MRI_eroded','Fusion_eroded'],main['metrics'])
    boot = read('reports/ucsd_fusion/paired_patient_bootstrap.csv')
    intervals(boot,main['patient_cluster_bootstrap_95ci'])
    single = read('data/processed/ucsd_stability_single_scan_oof.csv')
    stability = load('reports/ucsd_stability/metrics.json')
    assert (len(single),single.patient_id.nunique(),int(single.tumor_label.sum()))==(135,135,113)
    selection = read('reports/ucsd_stability/single_scan_selection.csv')
    assert set(single.ID)==set(selection.loc[selection.selected,'ID'])
    grouped(single); metrics(single,['M0','M1','MRI','Fusion'],stability['single_scan']['metrics'])
    intervals(read('reports/ucsd_stability/single_scan_patient_bootstrap.csv'),stability['single_scan']['bootstrap_95ci'])
    repeated = read('data/processed/ucsd_stability_repeated_oof.csv')
    repeated_metrics = read('reports/ucsd_stability/repeated_metrics.csv')
    assert repeated.repeat.nunique()==20 and len(repeated)==3640
    for n,g in repeated.groupby('repeat'):
        same_ids(d,g);grouped(g)
        saved = repeated_metrics[repeated_metrics.repeat.eq(n)].set_index('model').to_dict('index')
        metrics(g,['M0','M1','MRI','Fusion'],saved)
    first=repeated[repeated.repeat.eq(1)].set_index('ID').sort_index()
    for model in ['M0','M1','MRI','Fusion']:
        close(first[model+'_oof_probability'],pred.set_index('ID').sort_index()[model+'_oof_probability'])
    sources = read('reports/ucsd_batch_features/source_manifest.csv')
    qc = read('reports/ucsd_batch_features/actual_file_QC.csv')
    assert len(sources)==546 and not sources.duplicated(['ID','sequence']).any()
    assert set(sources.ID)==set(d.ID) and sources.groupby('ID').size().eq(3).all()
    assert sources.sha256.str.fullmatch('[0-9a-f]{64}').all()
    pd.testing.assert_frame_equal(sources[['ID','sequence','bytes','sha256']].sort_values(['ID','sequence']).reset_index(drop=True),
                                  qc[['ID','sequence','bytes','sha256']].sort_values(['ID','sequence']).reset_index(drop=True))
    return dict(status='PASS',source_commit=manifest['source_commit'],files_verified=len(manifest['files']),
                raw_clinical_scans=243,clinical_scans=238,primary_scans=182,primary_patients=135,
                tumor_scans=141,treatment_change_scans=41,missing_interval_scans=36,
                primary_auc=main['metrics']['Fusion']['roc_auc'],clinical_auc=main['metrics']['M1']['roc_auc'],
                paired_auc_increment=main['metrics']['Fusion']['roc_auc']-main['metrics']['M1']['roc_auc'],
                repeated_partitions=20,single_scan_patients=135,referenced_image_files=546,
                model_fits_performed=0,image_downloads_performed=0)

if __name__=='__main__':
    print(json.dumps(check(Path(__file__).parent),indent=2))
'''

def role(path):
    if path.startswith('data/raw/'): return 'original_public_source'
    if path.startswith('data/processed/'): return 'derived_analysis_data'
    if path.startswith('src/'): return 'original_analysis_code'
    if path.startswith('reports/'): return 'saved_result_or_audit'
    return 'provenance_or_environment'

def build(root):
    root=Path(root).resolve()
    dest=root/FOLDER
    dest.mkdir(parents=True,exist_ok=True)
    listing=subprocess.check_output(['git','ls-tree','-r',SOURCE_COMMIT],cwd=root,text=True)
    entries=[]
    for line in listing.splitlines():
        head,path=line.split('\t',1)
        if any(re.fullmatch(p,path) for p in PATTERNS):
            mode,kind,sha=head.split()
            entries.append(dict(path=path,git_blob_sha=sha,bytes=(root/path).stat().st_size))
    with tempfile.TemporaryDirectory(prefix='ucsd_essential_') as tmp:
        package=Path(tmp)/NAME;package.mkdir()
        for f in entries:
            data=(root/f['path']).read_bytes()
            assert len(data)==f['bytes']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==f['git_blob_sha'], f['path']
            p=package/f['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        (package/'README.md').write_text(README.format(commit=SOURCE_COMMIT))
        (package/'verify_package.py').write_text(VERIFY)
        (package/'requirements_verify.txt').write_text('pandas==2.2.3\nnumpy==2.3.5\nscipy==1.17.0\nscikit-learn==1.8.0\nopenpyxl==3.1.5\n')
        rows=[
            ['ID','Public examination identifier','text','join only'],
            ['patient_id','Public UCSD patient identifier','text','patient grouping'],
            ['BraTS ID','Public BraTS examination identifier','text','join only'],
            ['brats_patient_id','Public BraTS patient identifier','text','patient grouping'],
            ['validation_group','Combined patient grouping key','text','patient grouping'],
            ['tumor_label','1 residual/recurrent tumor; 0 treatment-related change','binary','outcome'],
            ['label_source','Origin of the binary label','text','audit'],
            ['age_years','Age at examination','years','M0 M1 Fusion'],
            ['sex_male','Male=1; Female=0 from source sex-at-birth field','binary','M0 M1 Fusion'],
            ['other_treatment_prior','Source other-treatment-before-scan: Yes=1 No=0','binary','M1 Fusion'],
            ['initial_event_offset_raw','Source offset from acquisition to initial surgery/treatment/diagnosis','days or Unknown','audit'],
            ['days_since_initial_event','Negative source offset converted to positive days; other entries missing','days','derived intermediate'],
            ['log_initial_event_days','Natural log of (1+days_since_initial_event); missing values retained','dimensionless','M1 Fusion'],
            ['initial_event_missing','Initial-event interval missing=1 observed=0','binary','M1 Fusion'],
            ['primary_diagnosis_raw','Unchanged source primary diagnosis text','text','audit'],
            ['validation_fold','Held-out patient-grouped fold number','integer 1..5','validation'],
            ['*_oof_probability','Out-of-fold probability for tumor_label=1','probability 0..1','saved model output'],
            ['*_prediction_0_5','Tumor probability >=0.5 gives 1, otherwise 0','binary','saved classification'],
            ['repeat / seed','Repeated partition index and saved random seed','integer','supplementary validation'],
            ['*_eroded*','MRI boundary sensitivity using one grid-voxel 6-neighbor erosion','see feature_dictionary.csv','supplementary analysis'],
            ['draw','Saved patient-cluster bootstrap draw index','integer','saved sampling result'],
        ]
        buffer=io.StringIO();w=csv.writer(buffer);w.writerow(['field','definition','unit_or_values','role']);w.writerows(rows)
        (package/'DATA_DICTIONARY.csv').write_text(buffer.getvalue())
        notebook=dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python')),
                      cells=[dict(cell_type='markdown',id='readme',metadata={},source=['# 核验论文必要数据\n','从此notebook所在目录运行。读取原始工作簿并核对固定分析数据、患者分组、AUC及已保存区间。无需MRI图像。']),
                             dict(cell_type='code',id='verify',execution_count=None,metadata={},outputs=[],source=['from pathlib import Path\n','import json\n','from verify_package import check\n','result = check(Path.cwd())\n','print(json.dumps(result, indent=2))'])])
        (package/'Verify_Essential_Data.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2)+'\n')
        bypath={f['path']:f for f in entries}
        manifest=dict(package=NAME,created_date='2026-10-30',source_commit=SOURCE_COMMIT,
                      scope='Original clinical sources and derived MRI-feature analysis data; voxel images referenced, not bundled',files=[])
        for p in sorted(package.rglob('*')):
            if p.is_file():
                rel=p.relative_to(package).as_posix();b=p.read_bytes();source=bypath.get(rel)
                manifest['files'].append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),
                                             role=role(rel) if source else 'package_documentation_or_verification',
                                             source_repository_path=rel if source else None,
                                             source_git_blob_sha=source['git_blob_sha'] if source else None))
        (package/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        report=json.loads(subprocess.check_output([__import__('sys').executable,str(package/'verify_package.py')],text=True))
        archive=dest/(NAME+'.zip')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in sorted(package.rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts:
                    info=zipfile.ZipInfo(p.relative_to(package.parent).as_posix(),date_time=(2026,10,30,0,0,0))
                    info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644<<16
                    z.writestr(info,p.read_bytes(),compresslevel=9)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert len(z.namelist())==len(manifest['files'])+1
        (dest/'MANIFEST.json').write_bytes((package/'MANIFEST.json').read_bytes())
        size=archive.stat().st_size
        report.update(archive=archive.name,archive_bytes=size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                      archive_git_blob_sha=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+archive.read_bytes()).hexdigest(),
                      archive_members=len(manifest['files'])+1,source_files=len(entries),source_payload_bytes=sum(f['bytes'] for f in entries),
                      verification='All payload hashes, raw-clinical reconstruction, primary/supplementary metrics and saved bootstrap intervals checked; no models refitted')
        (dest/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
        note='''# 论文必要数据压缩包

本文件夹存放论文Revision 1所需的精简数据快照。

- **[{name}.zip]({name}.zip)**：{mb:.2f} MB，{members}个文件。
- [MANIFEST.json](MANIFEST.json)：逐文件大小、SHA256、来源路径与Git blob SHA。
- [verification.json](verification.json)：样本、指标及压缩包校验结果。

压缩包含两份原始临床Excel工作簿、公开镜像参与者元数据、182次检查/135名患者的完整模型输入和MRI特征、患者分组、折外预测、补充分析数据，以及数据字典和Jupyter核验notebook。MRI体素文件通过546项来源清单保存地址和哈希，便于按需获取。

解压后先阅读包内README.md。需要核验时运行 `python verify_package.py`，或打开 `Verify_Essential_Data.ipynb`。本次整理没有修改标签、特征、预测或论文结果。

来源快照：[`{commit}`](https://github.com/BTomoto/rn-mri-clinical-fusion/tree/{commit})。
打包脚本：[`scripts/package_ucsd_essential_data.py`](../../scripts/package_ucsd_essential_data.py)。

当前数据包支持临床来源核对、特征级模型重分析和论文结果核对。从图像重新提取特征时，按包内影像清单获取对应图像。
'''
        (dest/'README.md').write_text(note.format(name=NAME,mb=size/1e6,members=report['archive_members'],commit=SOURCE_COMMIT))
        print(json.dumps(report,indent=2))

if __name__=='__main__':
    build(Path(__file__).resolve().parents[1])
