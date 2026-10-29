# Derived source-annotation union masks

Six masks are derived from the corresponding ordinary BraTS source segmentations by the single rule `source_label > 0`. All positive integer labels and all connected components are retained; no class-specific rule, filling, dilation or largest-component selection is used. The original native affine and unknown spatial-unit metadata are preserved. These are not pure-tumor or active-tumor masks.

Source files remain under `data/samples/ucsd_mirror/`; source and derived hashes are recorded in `reports/ucsd_roi_pilot/`. Reproduce with `python scripts/run_ucsd_roi_pilot.py`. The one-voxel erosion is only a processing sensitivity diagnostic, not the saved primary ROI. No TCT/ECT/NECT reference segmentation is used.

These files support the six-case technical pilot, not independent validation of source annotations or clinical prediction. Physical volume cannot be inferred without resolving spatial units. Attribution and license follow UCSD-PTGBM, data DOI https://doi.org/10.7937/fwv2-dt74 , CC BY 4.0, and mirror curator https://github.com/data-nih/tcia .
