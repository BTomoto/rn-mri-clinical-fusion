# Public MRI source data v0.1

Independent ZIP archives contain all available DICOM series for 107 selected
patient-date pairs from 59 pseudonymous OpenBTAI patients. There are 40,801
DICOM files, totaling 18,208,867,252 uncompressed bytes. The selection represents
temporally matched baseline and early MRI, not a final adjudicated prediction
cohort. Clinical source tables and executed curation notebooks are in the main
repository.

Every source member was verified against the original ZIP size and CRC32; the
repository contains SHA256 file manifests and archive-part hashes. Extract all
parts into the project root to restore `data/imaging/dicom/`. ZIP parts are
independent archives, not split-volume ZIP segments.

Data source: Ocaña-Tienda et al., Scientific Data (2023),
https://doi.org/10.1038/s41597-023-02123-0 . OpenBTAI source Figshare records
report CC0. No clinical prediction performance is claimed by this data release.
