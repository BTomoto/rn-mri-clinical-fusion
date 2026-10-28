"""All-file geometry and mask-grid audit for 54 current baseline candidates."""
from audit_additional_imaging import run


if __name__=='__main__':
    run(manifest_relative='data/metadata/baseline_qc/mask_series_members.jsonl',prefix='cohort',
        output_subdir='baseline-qc-20261028',scope='complete MRI series named by 54 baseline mask candidates; not all modalities',
        mask_candidates_only=True,write_overlays=False)
