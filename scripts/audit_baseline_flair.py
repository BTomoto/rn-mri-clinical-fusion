"""All-file FLAIR technical QC, without matching a T1 mask to a FLAIR grid."""
from audit_additional_imaging import run
if __name__=='__main__':
    run(manifest_relative='data/metadata/baseline_qc/flair_series_members.jsonl',prefix='flair',
        output_subdir='flair-grid-qc-20261028',scope='all named non-T1 FLAIR candidates in 48 baseline mask studies',
        write_overlays=False,include_mask_audit=False)
