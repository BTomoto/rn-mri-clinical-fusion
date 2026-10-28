"""Prepare pilot trials and endpoint evidence for a compact Excel review."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
frames=[]
for attempt,file in [('initial_gradient_descent','registration_pilot_initial_gradient_descent.csv'),('regular_step','registration_pilot.csv')]:
    f=pd.read_csv(ROOT/'data/processed'/file);f.insert(0,'attempt',attempt)
    if 'metric_screen_pass' not in f:f['metric_screen_pass']=0
    if 'candidate_status' not in f:f['candidate_status']='rejected_metric_or_overlap'
    frames.append(f)
cols=['attempt','lesion_key','negative_mi_before','negative_mi_after','metric_improved','metric_screen_pass','translation_norm_mm',
      'max_abs_rotation_degrees','foreground_fov_overlap_before','foreground_fov_overlap_after','target_coordinate_fov_before',
      'target_coordinate_fov_after','candidate_status','clinical_alignment_accepted','use_for_model']
f=pd.concat(frames).reindex(columns=cols)
gate=json.loads((ROOT/'reports/modeling_gate_20261029.json').read_text())
sources=[['2026-10-29','https://dw.molab.es/indices/bm1/OpenBTAI_METS_ClinicalData_Nov2023.xlsx','原作者临床文件SHA256与此前一致'],
 ['2026-10-29','https://www.nature.com/articles/s41597-023-02123-0','论文事件计数不能替代逐病灶无事件随访'],
 ['2026-10-29','https://pmc.ncbi.nlm.nih.gov/articles/PMC13490108/','诊断队列不等于治疗前风险队列；附录未完成字节获取'],
 ['2026-10-29','https://github.com/chamseddine-lab/rn-d3/tree/c4619bab9f27c102a25341ed838dea49fe9ac0c5','所查代码树只有合成示例registry'],
 ['2026-10-29','https://simpleitk.readthedocs.io/en/main/registrationOverview.html','配准变换方向及可复现设置方法']]
(ROOT/'reports/pilot_workbook_input.json').write_text(json.dumps(dict(headers=cols,rows=f.astype(object).where(f.notna(),None).values.tolist(),gate=gate,sources=sources),ensure_ascii=False,allow_nan=False))
print('Prepared 6 strategy/case records and endpoint gate')
