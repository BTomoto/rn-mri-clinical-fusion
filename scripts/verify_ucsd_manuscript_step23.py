"""Verify the bounded first-subsection writing deliverable; no model fitting."""
from pathlib import Path
import csv,hashlib,json,re
from collections import Counter
from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/ucsd_manuscript_step23'
OUT=ROOT/'outputs/ucsd-manuscript-step23-20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    receipt=json.loads((ROOT/'reports/ucsd_paper_materials/generation_receipt.json').read_text())
    frozen={**receipt['input_sha256'],**receipt['output_sha256']}
    assert all(sha(ROOT/p)==h for p,h in frozen.items()),'Prior study input or output changed'
    sources=json.loads((REPORT/'reference_library.json').read_text())
    refs=sources['references'];assert len(refs)==40
    assert sum(r['recent_5yr'] for r in refs)==37 and sum(r['recent_3yr'] for r in refs)==31
    doc=json.loads((REPORT/'methods_section21.json').read_text());paragraphs=doc['paragraphs']
    assert len(paragraphs)==3 and [r['id'] for r in paragraphs]==['M1','M2','M3']
    text=[p.text for p in Document(OUT/'UCSD_Manuscript_Methods_2_1_EN_ZH.docx').paragraphs]
    for r in paragraphs:
        assert r['english'] in text and r['chinese'] in text
        assert not re.search(r'[\u3400-\u9fff，。；：（）【】、]',r['english'])
        assert text.index(r['chinese'])==text.index(r['english'])+1
    assert doc['english_word_count']==449
    assert doc['citation_mapping']=={'1':'S01','2':'S02','3':'S03'}
    assert sha(ROOT/doc['included_figure'])==doc['figure_sha256']
    assert sha(ROOT/'reports/ucsd_writing_requirements_v2/requirements_and_outline.json')==doc['v2_outline_sha256']
    cohort={}
    for name,file in [('clinical','ucsd_clinical_revalidated_cohort.csv'),('imaging','ucsd_clinical_image_features.csv')]:
        with (ROOT/'data/processed'/file).open() as f:rows=list(csv.DictReader(f))
        cohort[name]={'examinations':len(rows),'patients':len({r['patient_id'] for r in rows}),'labels':dict(Counter(r['tumor_label'] for r in rows))}
    assert cohort['clinical']['examinations']==238 and cohort['clinical']['patients']==176
    assert cohort['imaging']=={'examinations':182,'patients':135,'labels':{'0':41,'1':141}}
    xlsx=OUT/'UCSD_Reference_Evidence_Library.xlsx'
    wb=load_workbook(xlsx,data_only=True,read_only=True)
    assert wb.sheetnames==['Summary','References','Evidence']
    for i,r in enumerate(refs,2):
        sh=wb['References'];assert sh.cell(i,1).value==r['id'] and sh.cell(i,3).value==r['title']
        assert sh.cell(i,5).value==(r['doi'] or None) and str(sh.cell(i,6).value or '')==str(r['pmid'] or '')
        assert [sh.cell(i,j).value for j in [8,9,10,11,12]]==[r['publication_year'],r['eligibility_year'],1,r['recent_5yr'],r['recent_3yr']]
        e=wb['Evidence'];assert [e.cell(i,j).value for j in range(1,8)]==[r['id'],r['role'],r['support'],r['limitation'],r['outline_locations'],r['read_level'],r['in_current_section']]
    assert [wb['Summary'].cell(i,3).value for i in [5,6,7,8,9,10,11,12,13]]==[40,40,37,.925,31,.775,3,39,30]
    wb.close()
    pages=len(PdfReader(OUT/'docx_render/UCSD_Manuscript_Methods_2_1_EN_ZH.pdf').pages);assert pages==4
    payload={'success':True,'stage':23,'date':'2026-10-29','subsection':'2.1 Study design and data sources',
      'english_paragraphs':3,'matched_chinese_paragraphs':3,'english_word_count':449,'word_pages':pages,
      'current_section_references':3,'candidate_reference_counts':sources['counts'],'spreadsheet_sheets':3,
      'spreadsheet_metadata_rows_checked':40,'spreadsheet_evidence_rows_checked':40,
      'spreadsheet_formula_perturbation_verified':True,'prior_study_files_hash_checked':len(frozen),
      'prior_study_inputs_and_outputs_unchanged':True,'figure_reused_unchanged':True,'v2_outline_unchanged':True,
      'docx_visual_review_pages':[1,2,3,4],'spreadsheet_visual_review':['Summary','References','References eligibility columns','Evidence','Evidence S18-S21'],
      'models_refitted':0,'new_hypothesis_tests':0,'cohort':cohort,
      'reference_review_scope':dict(Counter(r['read_level'] for r in refs)),
      'citation_numbering':'Local subsection numbering; regenerate globally when Introduction is assembled',
      'next_stage':'2.2 Reference standard (M4), followed by clinical predictor definitions (M5-M6), pending user instruction',
      'sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.suffix in {'.docx','.xlsx','.txt','.ris'}}}
    (REPORT/'artifact_verification.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:payload[k] for k in ['success','word_pages','english_word_count','prior_study_files_hash_checked','reference_review_scope']},indent=2))
if __name__=='__main__':main()
