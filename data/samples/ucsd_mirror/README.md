# Six small UCSD-PTGBM mirror technical samples

These 36 actual `.nii.gz` files were downloaded over public HTTPS from `https://github.com/data-nih/tcia/releases`. Stage15 acquired 0002_01/0005_01; Stage16 added 0006_01/0007_01/0008_02/0010_01, making six distinct source patients. Original mirror filenames and bytes are preserved; no re-encoding or resampling was applied. Each file is smaller than 2 MB. This is not the full cohort.

File URLs, mirror release SHA256 and bytes: `reports/ucsd_mri_mirror/selected_download_manifest.csv`. Actual transfer/QC: `reports/ucsd_mri_mirror/`. Re-download or verify from the project root with `python scripts/download_ucsd_mirror_samples.py`.

The complete six-case manifest and actual transfer/QC are in `reports/ucsd_roi_pilot/`; re-download or verify six cases with `python scripts/run_ucsd_roi_pilot.py`. The Stage15 command remains restricted to its historical two cases. Derived binary ROI masks are separate under `data/processed/ucsd_roi_pilot_masks/`.

The images decode, but header spatial units are unknown; intensity files are uint8 with values 0–255 and identity scaling. They must not be described as original quantitative ADC. Ordinary BraTS masks are supplied for technical review only; no TCT/ECT/NECT reference masks were downloaded. Prediction ROI and clinical validity are not established.

Attribution: Gagnon et al., UCSD-PTGBM, TCIA DOI https://doi.org/10.7937/fwv2-dt74; descriptor https://doi.org/10.1038/s41597-025-06499-z; original dataset CC BY 4.0 https://creativecommons.org/licenses/by/4.0/ . Mirror derivatives curated via Pittsburgh Fiber Data Hub (`data-nih/tcia`), https://github.com/data-nih/tcia . No claim of byte identity with original TCIA files is made.
