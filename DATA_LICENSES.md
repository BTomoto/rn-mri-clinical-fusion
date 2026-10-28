# Data provenance and licenses

The OpenBTAI Figshare clinical, morphological, radiomic, mask and DICOM records used here report CC0. Preserve source citations even where attribution is not a legal condition. Exact source URLs and hashes are in `data/metadata/source_files.json` and `archive_sources.json`.

Author-hosted OpenBTAI tables obtained from the MOLAB public download buttons are separately versioned under `data/raw/openbtai_molab_current/`. The source website requires citation of Ocaña-Tienda et al., Scientific Data (2023), DOI 10.1038/s41597-023-02123-0. No separate file-level license was observed for those direct downloads; the Figshare CC0 label is not automatically applied to them. Exact public endpoints, file URLs, archive-member provenance and SHA256 values are recorded under `data/metadata/endpoint_followup/`. No non-public clinical records were obtained.

The UCSD-BMETS-Longitudinal and Yale-Brain-Mets-Longitudinal TCIA reference files report CC BY 4.0 and require the collection citation. Their metadata-only reference copies are not treated as outcome-labeled radiation-necrosis cohorts.

The separate UCSD-PTGBM clinical-v3 and negative-case reference workbooks downloaded on 2026-10-29 are listed as CC BY 4.0 on the [official collection page](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/). Cite the collection and its [Scientific Data descriptor](https://doi.org/10.1038/s41597-025-06499-z). Exact file URLs and SHA256 values are retained under `data/metadata/public_label_audit_20261029/`. These are high-grade-glioma data, kept separate from the OpenBTAI brain-metastasis cohort. The derived feasibility table preserves explicit subtype text and distinguishes labels derived from the published overall partition.

RN-D3 supplementary-material bytes were read through the [Europe PMC public supplement endpoint](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13490108/supplementaryFiles?includeInlineImage=false). Only hashes, structure and audit findings are committed; the original DOCX and figures are not republished. Cite [the source article](https://doi.org/10.3389/frai.2026.1891883).

The PROTEAS clinical reference workbook was obtained from the open v5 record at https://zenodo.org/records/23171182. Its authors are Flouri et al.; cite https://doi.org/10.1038/s41597-025-06131-0 and the exact dataset version. Retain the repository's applicable license.

No new participant recruitment, biological intervention, animal work, or cell work is performed by this project. Dataset permissions and the original studies' provenance are retained independently of this study's public-data analysis scope.
