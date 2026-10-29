"""Actual six-case ROI review panels and processing histograms; no diagnostic scoring."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rn_public.ucsd_roi_pilot import SAMPLE_IDS, STRUCTURAL, normalize_values
OUT = ROOT/'outputs/ucsd-roi-pilot-20261029'
COLORS = {'FLAIR':'#0072B2','T1pre':'#009E73','T1post':'#D55E00','T2':'#CC79A7'}


def main():
    receipt = json.loads((ROOT/'reports/ucsd_roi_pilot/pilot_receipt.json').read_text())
    files = {(r['ID'], r['sequence']): r for r in receipt['files']}
    cases = {r['ID']: r for r in receipt['cases']}
    params = {(r['ID'], r['sequence']): r for r in receipt['normalization']}
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','savefig.facecolor':'white'})
    fig,axes = plt.subplots(6,2,figsize=(9,17),squeeze=False)
    for i,case in enumerate(SAMPLE_IDS):
        record = cases[case]
        if not record['success']:
            for ax in axes[i]:ax.text(.5,.5,record['error'],ha='center');ax.axis('off')
            continue
        image = nib.as_closest_canonical(nib.load(ROOT/record['derived_mask']))
        roi = np.asarray(image.dataobj)>0
        ero = ndimage.binary_erosion(roi,structure=ndimage.generate_binary_structure(3,1))
        z = int(np.argmax(roi.sum(axis=(0,1))))
        coords = np.where(roi[:,:,z]);lo = [max(0,int(x.min())-12) for x in coords]
        hi = [min(roi.shape[j],int(x.max())+13) for j,x in enumerate(coords)]
        crop = (slice(lo[0],hi[0]),slice(lo[1],hi[1]),z)
        rview,eview = roi[crop].T,ero[crop].T
        for j,seq in enumerate(['FLAIR','T1post']):
            img = nib.as_closest_canonical(nib.load(ROOT/files[(case,seq)]['path']))
            raw = np.asarray(img.dataobj)[crop].T
            ax=axes[i,j]
            ax.imshow(normalize_values(raw,params[(case,seq)]),cmap='gray',origin='lower',vmin=0,vmax=1,interpolation='nearest')
            for mask,color in [(rview,'#56B4E9'),(eview,'#E69F00')]:
                if mask.any() and not mask.all():ax.contour(mask.astype(float),levels=[.5],colors=[color],linewidths=.8)
            ax.set_title(f'{case.removeprefix("UCSD-PTGBM-")} | {seq} | ROI={record["roi_voxels"]:,} voxels',fontsize=10)
            ax.axis('off')
    fig.suptitle('Six-case technical review: one source-annotation union rule',fontsize=14,y=.994)
    handles=[Line2D([],[],color='#56B4E9',label='All positive ordinary mask codes'),Line2D([],[],color='#E69F00',label='One-voxel erosion (6-neighbour)')]
    fig.legend(handles=handles,loc='lower center',ncol=2,bbox_to_anchor=(.5,.025),fontsize=9)
    fig.text(.5,.011,'ROI-largest axial slice for review only. Header reorientation; physical units and absolute laterality unverified.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.025,right=.975,top=.973,bottom=.055,hspace=.32,wspace=.12)
    fig.savefig(OUT/'six_case_ROI_review.png',dpi=150)
    fig.savefig(OUT/'six_case_ROI_review.pdf')
    plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,7.3),squeeze=False)
    for ax,case in zip(axes.ravel(),SAMPLE_IDS):
        for seq in STRUCTURAL:
            r=params.get((case,seq))
            if not r or not r['histogram_success']:continue
            ax.plot(range(1,33),r['bin_probabilities'],color=COLORS[seq],label=seq,lw=1.2)
            if r['erosion_histogram_success']:
                e=np.array(r['eroded_bin_counts']);ax.plot(range(1,33),e/e.sum(),color=COLORS[seq],ls='--',lw=.7,alpha=.6)
        ax.set_title(case.removeprefix('UCSD-PTGBM-'),fontsize=11)
        ax.set_xlabel('Fixed bin index (32 bins)');ax.set_ylabel('ROI voxel proportion')
        ax.set_xlim(1,32);ax.set_ylim(bottom=0);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Prespecified clipped processing: union and one-voxel erosion',fontsize=14)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=4,bbox_to_anchor=(.5,.025))
    fig.text(.5,.008,'Solid: source union; dashed: erosion, using unchanged normalization and bin edges. No model or class comparison.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.075,1,.955),h_pad=1.5)
    fig.savefig(OUT/'six_case_intensity_histograms.png',dpi=180)
    fig.savefig(OUT/'six_case_intensity_histograms.pdf')
    plt.close(fig)
    followup=ROOT/'reports/ucsd_roi_pilot/unclipped_fixed_32_bin_histograms.csv'
    if followup.exists():
        h=pd.read_csv(followup)
        fig,axes=plt.subplots(2,3,figsize=(12,7.3),squeeze=False)
        for ax,case in zip(axes.ravel(),SAMPLE_IDS):
            for seq in STRUCTURAL:
                rows=h[h.ID.eq(case)&h.sequence.eq(seq)].sort_values('bin')
                if rows.empty:continue
                ax.plot(rows.bin,rows.probability,color=COLORS[seq],label=seq,lw=1.2)
                if rows.eroded_voxel_count.notna().all() and rows.eroded_voxel_count.sum()>0:
                    ax.plot(rows.bin,rows.eroded_voxel_count/rows.eroded_voxel_count.sum(),color=COLORS[seq],ls='--',lw=.7,alpha=.6)
            ax.set_title(case.removeprefix('UCSD-PTGBM-'),fontsize=11)
            ax.set_xlabel('Fixed bin index (32 bins)');ax.set_ylabel('ROI voxel proportion')
            ax.set_xlim(1,32);ax.set_ylim(bottom=0);ax.spines[['top','right']].set_visible(False)
        fig.suptitle('Unclipped affine processing: technical follow-up',fontsize=14)
        handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=4,bbox_to_anchor=(.5,.025))
        fig.text(.5,.008,'Added after observing clipping; no class or model-performance input. Solid: union; dashed: one-voxel erosion.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.075,1,.955),h_pad=1.5)
        fig.savefig(OUT/'six_case_unclipped_histograms.png',dpi=180)
        fig.savefig(OUT/'six_case_unclipped_histograms.pdf')
        plt.close(fig)
    print('Saved actual six-case ROI review and histogram figures')


if __name__=='__main__':main()
