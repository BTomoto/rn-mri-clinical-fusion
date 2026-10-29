"""Plot actual sample voxels; views are technical previews, not diagnostic adjudication."""
from pathlib import Path
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_mri_mirror import SAMPLE_IDS
OUT = ROOT/'outputs/ucsd-mri-mirror-20261029'
SEQS = ['FLAIR', 'T1pre', 'T1post', 'T2', 'ADC_vendor']
COLORS = ['#e69f00', '#56b4e9', '#cc79a7', '#009e73', '#d55e00', '#f0e442']


def load(record):
    img = nib.as_closest_canonical(nib.load(ROOT/record['relative_path']))
    return img.get_fdata(dtype=np.float32, caching='unchanged'), nib.affines.voxel_sizes(img.affine)


def plane(data, axis, index):
    return np.take(data, index, axis=axis).T


def draw(ax, data, spacing, axis, index, title):
    valid = data[np.isfinite(data) & (data != 0)]
    lo, hi = np.percentile(valid, [1, 99]) if valid.size else (0, 1)
    if lo == hi:
        hi = lo+1
    dims = [j for j in range(3) if j != axis]
    ax.imshow(plane(data, axis, index), origin='lower', cmap='gray', vmin=lo, vmax=hi,
              aspect=spacing[dims[1]]/spacing[dims[0]], interpolation='nearest')
    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    for x, y, text in [(0.01, .5, 'P' if axis == 0 else 'L'),
                        (.97, .5, 'A' if axis == 0 else 'R'),
                        (.5, .02, 'P' if axis == 2 else 'I'),
                        (.5, .96, 'A' if axis == 2 else 'S')]:
        ax.text(x, y, text, transform=ax.transAxes, color='white', fontsize=8,
                ha='center', va='center', bbox=dict(facecolor='black', alpha=.4, pad=1))


def main():
    receipt = json.loads((ROOT/'reports/ucsd_mri_mirror/sample_qc_receipt.json').read_text())
    files = {(r['ID'], r['sequence']): r for r in receipt['files']}
    if not all(r['decoded'] for r in files.values()):
        raise ValueError('Only actual fully decoded images can be plotted')
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'savefig.facecolor': 'white'})
    # Use the FLAIR nonzero-bounding-box midpoint, independent of labels/masks/outcomes.
    centers = {}
    for case in SAMPLE_IDS:
        data, spacing = load(files[(case, 'FLAIR')])
        nz = np.where(np.isfinite(data) & (data != 0))
        centers[case] = [int((x.min()+x.max())//2) for x in nz]
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 7.5))
    for i, case in enumerate(SAMPLE_IDS):
        data, spacing = load(files[(case, 'FLAIR')])
        for j, axis in enumerate([0, 1, 2]):
            draw(axes[i, j], data, spacing, axis, centers[case][axis],
                 f'{case.removeprefix("UCSD-PTGBM-")} FLAIR | '+['Sagittal', 'Coronal', 'Axial'][j])
    fig.suptitle('Actual mirror MRI samples: three voxel planes', fontsize=14)
    fig.text(.5, .015, 'Header RAS reorientation only; physical units and patient left/right not independently confirmed.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .03, 1, .96), h_pad=2.4)
    fig.savefig(OUT/'actual_FLAIR_planes.png', dpi=180)
    fig.savefig(OUT/'actual_FLAIR_planes.pdf')
    plt.close(fig)
    fig, axes = plt.subplots(2, 5, figsize=(15, 6.8))
    for i, case in enumerate(SAMPLE_IDS):
        for j, seq in enumerate(SEQS):
            r = files[(case, seq)]
            if r['relative_grid_to_FLAIR']['status'] != 'native_matrix_match':
                axes[i, j].text(.5, .5, 'Grid review required', ha='center')
                axes[i, j].axis('off')
                continue
            data, spacing = load(r)
            draw(axes[i, j], data, spacing, 2, centers[case][2], case.removeprefix('UCSD-PTGBM-')+' '+seq)
    fig.suptitle('Actual five-sequence samples: shared FLAIR-based axial index', fontsize=14)
    fig.text(.5, .015, 'Each panel uses its own 1st–99th percentile display window; brightness is not comparable between sequences.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.02, right=.99, top=.88, bottom=.09, wspace=.08, hspace=.32)
    fig.savefig(OUT/'actual_multisequence_axial.png', dpi=180)
    fig.savefig(OUT/'actual_multisequence_axial.pdf')
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 7.8))
    for i, case in enumerate(SAMPLE_IDS):
        r = files[(case, 'BraTS_tumor_seg')]
        base = files[(case, 'T1post')]
        if r['relative_grid_to_FLAIR']['status'] != 'native_matrix_match' or base['relative_grid_to_FLAIR']['status'] != 'native_matrix_match':
            for ax in axes[i]:
                ax.text(.5, .5, 'Grid review required', ha='center')
                ax.axis('off')
            continue
        data, spacing = load(base)
        seg, _ = load(r)
        labels = sorted(int(x) for x in np.unique(seg) if x > 0)
        # Fixed selected slices remain independent of mask size and clinical class.
        for j, axis in enumerate([0, 1, 2]):
            index = centers[case][axis]
            ax = axes[i, j]
            draw(ax, data, spacing, axis, index, case.removeprefix('UCSD-PTGBM-')+' T1post + raw segmentation')
            view = plane(seg, axis, index)
            for k, value in enumerate(labels):
                mask = view == value
                if mask.any() and not mask.all():
                    ax.contour(mask.astype(float), levels=[.5], colors=[COLORS[k % len(COLORS)]], linewidths=.8)
        handles = [Line2D([], [], color=COLORS[k % len(COLORS)], label=f'Observed code {v}') for k, v in enumerate(labels)]
        axes[i, 1].legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, -.01), ncol=max(1, len(labels)), fontsize=7)
    fig.suptitle('Ordinary BraTS mask contours: numeric codes only', fontsize=14)
    fig.text(.5, .01, 'Contours are source annotations for technical review. No tissue-code interpretation or prediction ROI approval.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, .96), h_pad=2.4)
    fig.savefig(OUT/'actual_segmentation_overlay.png', dpi=180)
    fig.savefig(OUT/'actual_segmentation_overlay.pdf')
    plt.close(fig)
    print('Saved three actual-image technical previews')


if __name__ == '__main__':
    main()
