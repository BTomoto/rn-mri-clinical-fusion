"""Prepare a traceable 40-reference candidate library without republishing abstracts."""
import argparse,hashlib,html,json,re,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
from difflib import SequenceMatcher

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/ucsd_manuscript_step23'
OUT=ROOT/'outputs/ucsd-manuscript-step23-20261029'
BASE_IDS='41495087 38626948 38809149 37774317 40827022 42548620 42332872 42105112 41237487 40854380 39380365 36711062 36968291 37118754 33535988 42898007 40768078 42565942 42567711 40722849 41803972 38319168 40127903 38191193 38224968 38253388 38418819 38729274 39607450 40982167 38596719 32154773'.split()
EXTRA_IDS='38228979 37142815 39122953 38926092 38347141 37672053 39990680'.split()
# Support and limitations are concise original screening notes, not article abstracts.
NOTES=[
 ('Data source','Describes the UCSD-PTGBM cohort, source imaging and annotations, de-identification and original ethics approval.','Source collection differs from our derived mirror; source acquisition units do not establish units in the mirror.','M1-M4, M7-M8, D8-D9'),
 ('Reporting','Provides reporting guidance for regression and machine-learning prediction models.','Reporting guidance does not establish low risk of bias or clinical usefulness.','M1, M20'),
 ('Reporting','Lists imaging-AI reporting items covering data, reference standards, partitions, performance and errors.','The complete official checklist was reviewed; no claim that every item has already been fulfilled.','M1, M7-M20'),
 ('Clinical criteria','Updates response assessment in adult glioma trials, including confirmation in settings with frequent pseudoprogression.','Our inherited broad treatment-change labels were not independently re-adjudicated using RANO 2.0.','I2, D8'),
 ('Clinical context','Reviews contemporary management and molecular classification of adult glioblastoma.','The source cohort includes mixed historical diagnostic records; do not label all cases modern IDH-wildtype glioblastoma.','I1-I2, D8'),
 ('Fusion study','Examines a radiomics and clinical-imaging model in 222 patients with internally evaluated incremental performance.','Different predictors, reference standard and validation design; reported performance is not a direct benchmark.','I4, D2'),
 ('Fusion study','Evaluates voxel-wise habitat metrics with clinical and molecular inputs in training and external test samples.','Uses different sequences, features and reference definitions; external testing does not validate our model.','I4, D2'),
 ('Fusion study','Combines ConvNeXt and radiomics signatures with clinical factors in a multicenter glioma study.','Different model complexity and evaluation; detailed comparison requires full-text review.','I4, D2'),
 ('MRI study','Studies multisequence radiomics for recurrence versus pseudoprogression, including an independent test cohort.','Uses more modalities and selected high-dimensional inputs; do not transfer its clinical-readiness conclusion.','I3-I4, D2'),
 ('MRI study','Investigates pre- and postoperative enhanced-T1 deep features and clinical information for treatment-response classification.','Temporal inputs differ from current-scan diagnosis; detailed leakage and validation assessment requires full text.','I3-I4, D2'),
 ('ROI study','Combines intratumoral and peritumoral radiomics and compares imaging-region signatures.','Small split-sample cohort and different ROI definitions; not evidence for our specific one-voxel erosion rule.','I3, D2, D6'),
 ('Fusion study','Compares radiomics alone and radiomics with MGMT in a pathology-confirmed surgical cohort.','Surgical selection, perfusion inputs and pathology-only outcome differ; online publication was in 2022.','I4, D2-D3'),
 ('Negative evidence','Finds no reliable added benefit from several imaging combinations over a clinical and MGMT reference.','One selected single-center cohort; do not infer that radiomics always reduces performance.','I4-I5, D3'),
 ('Validation study','Applies a small multiparametric MRI model to a new glioblastoma cohort.','Mixed-tumor categorization differs between development and evaluation; not external validation of our model.','I4, D3'),
 ('Historical study','Evaluates conventional enhanced-T1 radiomics against readers in a small post-treatment cohort.','Older than the five-year window; no reader comparison was performed in our study.','I3, D3'),
 ('Evidence synthesis','Synthesizes externally tested MRI machine-learning diagnostic performance and documents limited external evidence.','Pooled performance spans heterogeneous studies and is not a target or acceptance threshold for our model.','I4-I5, D2-D3, D11'),
 ('Evidence synthesis','Summarizes AI performance for progression versus pseudoprogression across high-grade glioma studies.','Heterogeneous cohorts and standards; avoid importing pooled accuracy into this cohort.','I4, D3'),
 ('Clinical framework','Reviews clinical modifiers and tiered imaging assessment for treatment effects versus progression.','Proposed framework is not a validated decision tool and includes imaging modalities absent here.','I2, D8, D11-D12'),
 ('Same parent dataset','Uses 171 scans from 130 patients in UCSD-PTGBM to compare radio-pathomic, diffusion and perfusion features.','Shared parent cohort and different subset/labels; neither an independent external cohort nor proof of our novelty.','I5, D2-D3'),
 ('Clinical review','Discusses radiomics and radiogenomics for progression, pseudoprogression and radiation necrosis.','A broad review rather than a validation of these eight features or a unified diagnostic reference.','I2-I4, D8'),
 ('Clinical review','Reviews recurrence prediction, localization and differentiation from treatment effects in glioblastoma.','Future-risk prediction and current-status discrimination are distinct tasks.','I1-I5, D2-D3'),
 ('Standardization','Establishes reference filters and values for reproducible filtered-image radiomics.','Our pipeline has no convolutional filter features; citation provides context, not certification of implementation.','D4, D9'),
 ('Bias appraisal','Provides an updated quality, bias and applicability framework for prediction-model development and evaluation.','No formal independent PROBAST+AI appraisal was completed for this project.','D8-D11'),
 ('Validation guidance','Explains internal, internal-external and external evaluation and transportability of prediction models.','Our grouped cross-validation remains internal evaluation.','M13-M16, D6, D10-D11'),
 ('Validation guidance','Describes design and performance assessment in external validation studies.','An external dataset is not available here; guidance informs interpretation and future work.','D10-D12'),
 ('Sample-size guidance','Explains precision-based planning of external validation sample sizes rather than simple rules of thumb.','Our sample was availability-based; no retrospective power or formal prospective sample-size claim.','M20, D10, D12'),
 ('Leakage study','Demonstrates performance inflation from feature-selection leakage and repeated subjects in connectome models.','Different neuroimaging task; does not quantify bias in our cohort or eliminate annotation-related risks.','I5, M13, D6, D10'),
 ('Validation interpretation','Clarifies why one external validation is not automatically a license for implementation.','A methodological argument, not evidence that this model can bypass independent clinical evaluation.','D11-D12'),
 ('MRI preprocessing','Examines how intensity standardization and harmonization affect multicenter glioblastoma survival models.','Survival endpoint differs; better discrimination may coexist with poorer calibration or stability.','M9, D9-D11'),
 ('MRI repeatability','Uses repeated scans to assess diffusion and perfusion radiomic repeatability in glioblastoma.','Different quantitative sequences; no test-retest experiment was performed on our derived images.','D6, D9'),
 ('MRI preprocessing','Tests diffusion normalization and glioma molecular classification with external evaluation.','Different endpoint and ADC measurements; does not justify quantitative ADC use in our uint8 inputs.','D9'),
 ('Feature definitions','Provides standardized handcrafted feature definitions and benchmark values.','Older methodological reference; our hand-checked calculations are not complete IBSI certification.','M10-M11, D9'),
 ('Quality framework','Defines METRICS categories for methodological quality of radiomics studies.','We have not generated a METRICS score; no quality score is inferred from reporting alone.','I5, D4, D10'),
 ('Radiomics reporting','Specifies radiomics reporting details for image processing, features, reliability and validation.','Guideline use does not mean reader reproducibility or software benchmark testing was completed.','M7-M20, D9'),
 ('Leakage guidance','Describes dependency-aware questions for identifying leakage between model development and evaluation.','General biological learning guidance; outcome-informed annotation risk remains a separate issue.','M13, D8, D10'),
 ('Clinical criteria','Explains practical implementation of RANO 2.0 in adult glioma imaging trials.','Our records do not permit a new RANO 2.0 clinical adjudication.','I2, D8'),
 ('Metrics guidance','Connects validation metric selection with task, dataset and decision context.','Metric recommendations do not convert AUC into demonstrated clinical utility.','M14-M16, D11'),
 ('MRI preprocessing','Studies normalization effects on glioma subtype models and external generalization.','First online in 2023 despite a 2024 issue; molecular classification differs from this diagnostic task.','M9, D9'),
 ('MRI preprocessing','Compares intensity normalization and resulting radiomics across multiple organs and MRI acquisition settings.','Results do not establish that our percentile transformation is optimal or restore original image intensities.','M9, D9'),
 ('Software','Documents the scikit-learn machine-learning library used in our implementation.','The 2011 software paper does not specify the behavior of installed version 1.8.0; retain versioned code and documentation.','M12-M13, M20'),
]


def text(node):return ' '.join(''.join(node.itertext()).split()) if node is not None else ''
def digest(data):return hashlib.sha256(data).hexdigest()
def clean_title(s):
    s=html.unescape(re.sub('<[^>]+>','',s)).strip().rstrip('.')
    return s.replace('Progressionin','Progression in').replace('Combinedwith','Combined with')


def prepare(cache):
    cache.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    roots=[];sources=[]
    for filename,ids in [('pubmed_bulk.xml',BASE_IDS),('pubmed_additional.xml',EXTRA_IDS)]:
        p=cache/filename
        url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id='+','.join(ids)+'&retmode=xml'
        if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=45).read())
        data=p.read_bytes();roots.append(ET.fromstring(data));sources.append({'source':'NCBI PubMed','url':url,'bytes':len(data),'sha256':digest(data)})
    records={a.findtext('./MedlineCitation/PMID'):a for r in roots for a in r.findall('PubmedArticle')}
    assert len(records)==39 and len(NOTES)==40
    refs=[]
    full={'41495087','38626948','42548620','36711062','36968291','37118754','33535988'}
    for i,pid in enumerate(BASE_IDS+EXTRA_IDS):
        raw=records[pid];a=raw.find('./MedlineCitation/Article');j=a.find('Journal');pd=j.find('JournalIssue/PubDate')
        year=int(pd.findtext('Year') or re.search(r'\d{4}',pd.findtext('MedlineDate')).group())
        electronic=[text(d.find('Year'))+'-'+(d.findtext('Month') or '01').zfill(2)+'-'+(d.findtext('Day') or '01').zfill(2) for d in a.findall('ArticleDate') if d.get('DateType')=='Electronic']
        count_year=min([year]+[int(d[:4]) for d in electronic]);assert count_year<=2026
        assert all(d<='2026-10-29' for d in electronic)
        authors=[(n.findtext('LastName','')+' '+n.findtext('Initials','')).strip() for n in a.findall('AuthorList/Author') if n.findtext('LastName')]
        ids={n.get('IdType'):n.text for n in raw.findall('./PubmedData/ArticleIdList/ArticleId')}
        langs=[x.text for x in a.findall('Language')];assert langs==['eng'],(pid,langs)
        doi=ids['doi'];crpath=cache/'crossref'/f'{pid}.json';cr=None;sim=None
        if crpath.exists():
            cr=json.loads(crpath.read_text())['message'];assert cr['DOI'].lower()==doi.lower()
            norm=lambda s:re.sub('[^a-z0-9]','',clean_title(s).lower())
            sim=SequenceMatcher(None,norm(text(a.find('ArticleTitle'))),norm(cr['title'][0])).ratio();assert sim>.88,(pid,sim)
        role,support,limit,locations=NOTES[i]
        volume=j.findtext('JournalIssue/Volume','');issue=j.findtext('JournalIssue/Issue','')
        pages=a.findtext('Pagination/StartPage') or a.findtext('Pagination/MedlinePgn') or next((x.text for x in a.findall('ELocationID') if x.get('EIdType')=='pii'),'')
        journal=j.findtext('ISOAbbreviation') or text(j.find('Title'))
        ref={'id':f'S{i+1:02d}','pmid':pid,'pmcid':ids.get('pmc'),'doi':doi,'title_raw':text(a.find('ArticleTitle')),
             'title':clean_title(text(a.find('ArticleTitle'))),'authors':authors,'first_author':authors[0],
             'journal':journal,'publication_year':year,'electronic_dates':electronic,'eligibility_year':count_year,
             'volume':volume,'issue':issue,'pages_or_article':pages,'language':'English','english_flag':1,
             'recent_5yr':int(2022<=count_year<=2026),'recent_3yr':int(2024<=count_year<=2026),
             'source_url':f'https://pubmed.ncbi.nlm.nih.gov/{pid}/','doi_url':'https://doi.org/'+doi,
             'publication_types':[p.text for p in a.findall('PublicationTypeList/PublicationType')],
             'support':support,'limitation':limit,'role':role,'outline_locations':locations,
             'read_level':'Full text reviewed for relevant claims' if pid in full else 'Official full checklist reviewed' if pid=='38809149' else 'Abstract screened; full text needed before detailed comparison',
             'in_current_section':int(i<3),'pubmed_record_sha256':digest(ET.tostring(raw)),
             'doi_verification':'PubMed and Crossref' if cr else 'PubMed; secondary Crossref rate limited',
             'crossref_title_similarity':sim}
        auth=', '.join(authors[:6])+(', et al' if len(authors)>6 else '')
        tail=str(year)+((';'+volume+('('+issue+')' if issue else '')+(':'+pages if pages else '')) if volume else '')
        ref['citation']=f"{auth}. {ref['title']}. {journal}. {tail}. doi: {doi}."
        refs.append(ref)
    role,support,limit,locations=NOTES[-1]
    jurl='https://www.jmlr.org/papers/v12/pedregosa11a.html';jpath=cache/'scikit_jmlr.html'
    if not jpath.exists():jpath.write_bytes(urllib.request.urlopen(jurl,timeout=25).read())
    jb=jpath.read_bytes();assert b'2825' in jb and b'2011' in jb and b'Pedregosa' in jb
    refs.append({'id':'S40','pmid':None,'pmcid':None,'doi':None,'title_raw':'Scikit-learn: Machine Learning in Python','title':'Scikit-learn: Machine Learning in Python',
       'authors':['Pedregosa F','Varoquaux G','Gramfort A','Michel V','Thirion B','Grisel O','Blondel M','Prettenhofer P','Weiss R','Dubourg V','Vanderplas J','Passos A','Cournapeau D','Brucher M','Perrot M','Duchesnay E'],
       'first_author':'Pedregosa F','journal':'J Mach Learn Res','publication_year':2011,'electronic_dates':[],'eligibility_year':2011,
       'volume':'12','issue':'85','pages_or_article':'2825-2830','language':'English','english_flag':1,'recent_5yr':0,'recent_3yr':0,
       'source_url':jurl,'doi_url':None,'publication_types':['Software paper'],'support':support,'limitation':limit,'role':role,
       'outline_locations':locations,'read_level':'Publisher metadata and abstract reviewed','in_current_section':0,
       'doi_verification':'No DOI assigned in publisher citation','publisher_page_sha256':digest(jb),
       'citation':'Pedregosa F, Varoquaux G, Gramfort A, Michel V, Thirion B, Grisel O, et al. Scikit-learn: Machine Learning in Python. J Mach Learn Res. 2011;12:2825-2830. Available from: '+jurl})
    assert len({r['id'] for r in refs})==len(refs)==40
    assert len({r['doi'].lower() for r in refs if r['doi']})==39
    counts={'candidate_references':40,'english':40,'recent_5yr':sum(r['recent_5yr'] for r in refs),'recent_3yr':sum(r['recent_3yr'] for r in refs),
       'pubmed_records_verified':39,'doi_metadata_verified':39,'crossref_secondary_verified':sum(r.get('doi_verification')=='PubMed and Crossref' for r in refs),
       'current_section_cited':3,'final_manuscript_citation_list_complete':False}
    assert counts['recent_5yr']>=37 and counts['recent_3yr']>=25,counts
    payload={'date':'2026-10-29','status':'screened candidate evidence library; not a claim of 40 completed full-text reviews or final manuscript citations',
       'year_rule':'Earliest explicit electronic publication year or journal issue year; DOI year is not used. As-of date 2026-10-29.',
       'selection':'focused topic and methods search, not a systematic review; clinical outcomes, clinical-imaging fusion, adverse evidence, preprocessing, validation and reporting',
       'counts':counts,'sources':sources+[{'source':'JMLR','url':jurl,'bytes':len(jb),'sha256':digest(jb)}],'references':refs}
    (REPORT/'reference_library.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    ris=[]
    for r in refs:
        lines=['TY  - JOUR','ID  - '+r['id'],'TI  - '+r['title'],'JO  - '+r['journal'],'PY  - '+str(r['publication_year'])]
        lines += ['AU  - '+n for n in r['authors']]
        if r['doi']:lines.append('DO  - '+r['doi'])
        lines.extend(['UR  - '+r['source_url'],'N1  - '+r['id']+'; eligibility year '+str(r['eligibility_year'])+'; '+r['read_level'],'ER  -']);ris.append('\n'.join(lines))
    (OUT/'UCSD_Candidate_References.ris').write_text('\n\n'.join(ris)+'\n')
    (OUT/'UCSD_Candidate_References.txt').write_text('\n\n'.join('['+r['id']+'] '+r['citation'] for r in refs)+'\n')
    print(json.dumps(counts,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);prepare(p.parse_args().cache)
