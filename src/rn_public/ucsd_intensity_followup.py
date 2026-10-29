"""Explicit post-observation engineering comparison: retain intensity tails, no class input."""
from pathlib import Path
import json
import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.spatial.distance import jensenshannon
from .ucsd_roi_pilot import fixed_bins, STRUCTURAL
from .ucsd_mri_intake import sha256


def affine_values(values, params):
    a = np.asarray(values, dtype=np.float64)
    if not a.size or not np.isfinite(a).all() or params['p99'] <= params['p01']:
        raise ValueError('invalid_affine_intensity_scale')
    return (a-params['p01'])/(params['p99']-params['p01'])


def run(root):
    root = Path(root);out = root/'reports/ucsd_roi_pilot'
    original = json.loads((out/'pilot_receipt.json').read_text())
    cases = {r['ID']:r for r in original['cases'] if r['success']}
    files = {(r['ID'],r['sequence']):r for r in original['files']}
    result, histogram = [], []
    for case, r in cases.items():
        roi_path = root/r['derived_mask']
        if sha256(roi_path) != r['derived_mask_sha256']:raise ValueError('ROI_changed')
        roi = np.asarray(nib.load(roi_path).dataobj)>0
        erosion = ndimage.binary_erosion(roi,structure=ndimage.generate_binary_structure(3,1))
        for old in [x for x in original['normalization'] if x['ID']==case and x['sequence'] in STRUCTURAL]:
            record=files[(case,old['sequence'])];path=root/record['path']
            if sha256(path)!=record['sha256']:raise ValueError('source_image_changed')
            a=np.asarray(nib.load(path).dataobj);v=affine_values(a[roi],old)
            row=dict(ID=case,sequence=old['sequence'],method='p01_p99_affine_unclipped',
                     p01=old['p01'],p99=old['p99'],roi_voxels=int(roi.sum()),
                     normalized_minimum=float(v.min()),normalized_maximum=float(v.max()),
                     normalized_mean=float(v.mean()),normalized_std=float(v.std()),
                     below_zero_fraction=float(np.mean(v<0)),above_one_fraction=float(np.mean(v>1)),
                     occupied_bins=None,erosion_JS_distance=None,success=False,error=None)
            try:
                bins,lo,hi=fixed_bins(v);count=np.bincount(bins,minlength=33)[1:];p=count/count.sum()
                if erosion.any():
                    eb,_,_=fixed_bins(affine_values(a[erosion],old),minimum=lo,maximum=hi)
                    ec=np.bincount(eb,minlength=33)[1:];js=float(jensenshannon(p,ec/ec.sum(),base=2))
                else:ec=None;js=None
                row.update(success=True,occupied_bins=int(np.count_nonzero(count)),erosion_JS_distance=js,
                           JS_to_clipped=float(jensenshannon(p,np.array(old['bin_probabilities']),base=2)))
                for b in range(32):histogram.append(dict(ID=case,sequence=old['sequence'],bin=b+1,
                    voxel_count=int(count[b]),probability=float(p[b]),
                    eroded_voxel_count=None if ec is None else int(ec[b])))
            except ValueError as exc:row['error']=str(exc)
            result.append(row)
    table=pd.DataFrame(result);table.to_csv(out/'unclipped_normalization_diagnostics.csv',index=False)
    pd.DataFrame(histogram).to_csv(out/'unclipped_fixed_32_bin_histograms.csv',index=False)
    choice=dict(recommended_next_stage_method='per_image_p01_p99_affine_unclipped_then_ROI_FBN32',
                added_after_observing_clipping=True,uses_clinical_class=False,model_performance_used=False,
                reason='Avoid additional tail collapse measured under the original clipping rule',
                original_clipping_outputs_preserved=True,structural_records=len(table),
                successful_records=int(table.success.sum()),quantitative_ADC_allowed=False,
                physical_volume_allowed=False,independent_optimality_validated=False,
                amendment_sha256=sha256(root/'reports/ucsd_roi_pilot_intensity_amendment.md'),
                code_sha256=sha256(Path(__file__)))
    (out/'normalization_choice.json').write_text(json.dumps(choice,indent=2)+'\n')
    return choice
