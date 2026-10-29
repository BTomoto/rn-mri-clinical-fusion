"""Build the read-only MRI intake notebook; no simulated patients or model fits."""
from pathlib import Path
import sys
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb = nbf.v4.new_notebook(cells=[
    md('# 14 MRI文件接收、技术质控与ROI边界\n\n本步获准继续。固定规则见`reports/ucsd_mri_intake_protocol.md`。两例仅为技术样本，不估计性能。缺少文件时实际执行程序并输出blocked，不伪造影像、ROI或AUC。下列代码不读取临床标签，不生成模拟影像。'),
    code("from pathlib import Path\nimport sys,json,hashlib\nimport pandas as pd\nfrom IPython.display import display\nROOT=Path.cwd()\nif ROOT.name=='notebooks':ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT/'src'))\nfrom rn_public.ucsd_mri_intake import run,CASES,SEQUENCES\nresult=run(ROOT)\ns=result['summary']\nprint(json.dumps(s,ensure_ascii=False,indent=2))"),
    md('## 逐文件状态\n\n12行是两例扩展清单，不代表12份影像已到位；其中两份FLAIR是最小批次。重复文件、病例目录冲突及链接均拦截。'),
    code("checklist=pd.read_csv(ROOT/'reports/ucsd_mri_intake/sample_file_checklist.csv')\nassert len(checklist)==len(CASES)*len(SEQUENCES)==12\nassert checklist.expected_filename.is_unique\nassert checklist.minimal_batch.sum()==2\ndisplay(checklist[['ID','sequence','minimal_batch','status','decoded','technical_pass']])"),
    md('## 完整体素及几何读取的结果\n\nNiBabel头部载入是延迟读取；实际质控需gzip全流CRC及完整缩放体素读取。技术通过不等于解剖内容配准通过。下面只显示真实接收文件结果；没有文件时表格为空。'),
    code("located=[r for r in result['files'] if r['status']!='missing']\ndisplay(pd.DataFrame(located))\nprint('Actual expected files decoded:',s['decoded_expected_files'])\nprint('Minimal FLAIR batch technical pass:',s['minimal_FLAIR_batch_technical_pass'])\nassert s['decoded_expected_files']==sum(r['decoded'] for r in result['files'])"),
    md('## ROI与来源证据门槛\n\nTCT/ECT/NECT参考分割禁止作为预测输入；普通BraTS也尚未确认盲法及标签含义，不自动授权预测ROI。SHA256只是本地内容指纹，没有官方逐文件哈希，不能证明来源。实际图像及后续审阅未完成时不建立MRI模型。'),
    code("print('Excluded inputs:',json.dumps(result['excluded_files'],ensure_ascii=False,indent=2))\nassert s['ROI_for_prediction_approved'] is False\nassert s['MRI_features_extracted'] is False and s['MRI_model_fitted'] is False\nassert s['clinical_models_refitted'] is False\nprotocol=ROOT/'reports/ucsd_mri_intake_protocol.md'\nassert s['protocol_sha256']==hashlib.sha256(protocol.read_bytes()).hexdigest()\nprint('Current state:',s['state'])"),
    md('## 软件验证与真实研究数据分开\n\n自动测试使用临时小数组注入截断文件、非有限值、坐标冲突、空掩膜等错误；临时测试文件不计为实际UCSD影像。软件测试回执可复核。当前仍需真实文件，下一研究阶段等待用户批准。'),
    code("receipt=ROOT/'reports/ucsd_mri_intake/software_test_receipt.json'\nif receipt.exists():\n    print(receipt.read_text())\nelse:\n    print('Software tests must be run separately; no test success claimed by this notebook.')\nprint('No clinical model or MRI diagnostic performance estimated in this step.')")
])
nb.metadata = {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
               'language_info': {'name': 'python', 'version': sys.version.split()[0]}}
nbf.write(nb, ROOT/'notebooks/14_ucsd_mri_intake_and_qc.ipynb')
print('Created Notebook14')
