"""Assemble confirmed manuscript text and editable objects; never fit or resample models."""
from pathlib import Path
from copy import deepcopy
import json,re,hashlib,argparse,zipfile,csv
from lxml import etree
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START,WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ucsd-manuscript-step55-20261030'
REPORT=ROOT/'reports/ucsd_manuscript_step55'
TITLE='Clinical-MRI Feature Fusion for Distinguishing Residual or Recurrent Tumor from Treatment-Related Changes after Glioma Treatment: A Public-Data Internal Validation Study'
KEYWORDS=['high-grade glioma','treatment-related change','magnetic resonance imaging','feature fusion','logistic regression','internal validation']
ABSTRACT=json.loads((REPORT/'abstract_content.json').read_text())
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def wc(s):return len(re.findall(r"[A-Za-z0-9]+(?:['/-][A-Za-z0-9]+)*",s))
def canonical(e):return etree.tostring(e,method='c14n',exclusive=True)
def load_sources():
    paths=[ROOT/'reports/ucsd_manuscript_step54/introduction_section54.json']
    paths += [next((ROOT/f'reports/ucsd_manuscript_step{n}').glob('methods_section*.json')) for n in range(23,33)]
    paths += [next((ROOT/f'reports/ucsd_manuscript_step{n}').glob('results_section*.json')) for n in range(33,41)]
    paths += [ROOT/f'reports/ucsd_manuscript_step{n}/discussion_section{n}.json' for n in range(41,53)]
    paths += [ROOT/'reports/ucsd_manuscript_step53/conclusion_section53.json']
    sections=[json.loads(p.read_text()) for p in paths]
    oldmap={};refs={r['id']:r['citation'] for r in json.loads((ROOT/'reports/ucsd_manuscript_step23/reference_library.json').read_text())['references']}
    for d in sorted(sections,key=lambda x:x['stage']):
        for number,rid in d.get('citation_mapping',{}).items():
            assert number not in oldmap or oldmap[number]==rid
            oldmap[number]=rid
        for r in d.get('source_audit',{}).get('reference_records',[]):refs[r['reference_id']]=r['citation']
        if 'reference_used' in d:refs[d['reference_used']['id']]=d['reference_used']['citation']
    numbering={}
    for d in sections:
        for p in d['paragraphs']:
            seen=[]
            for group in re.findall(r'\(([0-9]+(?:\s*,\s*[0-9]+)*)\)',p['english']):
                for old in group.split(','):
                    rid=oldmap[old.strip()];seen.append(rid)
                    if rid not in numbering:numbering[rid]=len(numbering)+1
            assert set(seen)==set(p['citation_ids']),(p['id'],seen)
    assert len(numbering)==25 and sum(wc(p['english']) for d in sections for p in d['paragraphs'])==8200
    return paths,sections,oldmap,refs,numbering

def renumber(s,oldmap,numbering):
    def one(m):return '('+','.join(str(numbering[oldmap[x.strip()]]) for x in re.split('[,，]',m.group(1)))+')'
    s=re.sub(r'\(([0-9]+(?:\s*,\s*[0-9]+)*)\)',one,s)
    def zh(m):return '（'+','.join(str(numbering[oldmap[x.strip()]]) for x in re.split('[,，]',m.group(1)))+'）'
    return re.sub(r'（([0-9]+(?:\s*[,，]\s*[0-9]+)*)）',zh,s)

def objects(sections):
    equations={};tables={};figures={}
    for d in sections:
        if d['stage'] in range(23,33):
            current=None
            for e in Document(ROOT/d['docx']).element.body:
                t=''.join(e.xpath('.//w:t/text()'))
                for p in d['paragraphs']:
                    if t==p['english']:current=p['id']
                if e.xpath('.//m:oMath'):
                    assert current
                    equations.setdefault(current,[]).append(deepcopy(e))
        audit=d.get('source_audit',{})
        ts=audit.get('translated_tables',[])
        if 'translated_table' in audit:ts=[audit['translated_table']]
        for t in ts:tables[t['key']]=deepcopy(t)
        if d.get('included_figure') and d.get('figure_caption'):
            key=re.match(r'(Figure\s+S?\d+)',d['figure_caption']).group(1)
            figures[key]={'path':d['included_figure'],'caption':d['figure_caption'],'sha256':d['figure_sha256']}
    assert sum(len(v) for v in equations.values())==10 and len(tables)==10 and len(figures)==5
    return equations,tables,figures

def table_s2():
    source=list(csv.DictReader((ROOT/'outputs/ucsd-paper-materials-20261029/tables/TableS2.csv').open()))
    descriptions=[
      ('Age at imaging','Years; standardized within each training fold.'),
      ('Male sex at birth','Male=1, female=0; not scaled.'),
      ('Interval since initial event','Natural log of one plus elapsed days; training-fold median imputation and standardization.'),
      ('Other treatment before imaging','Yes=1, no=0; not scaled.'),
      ('Missing initial-event interval','Missing=1, observed=0; not scaled.'),
      ('FLAIR mean','Dimensionless, unclipped percentile-scaled ROI mean; training-fold standardization.'),
      ('FLAIR standard deviation','Dimensionless; population SD (ddof=0); training-fold standardization.'),
      ('FLAIR entropy','Bits; Shannon entropy with 32 ROI-range bins; training-fold standardization.'),
      ('FLAIR GLCM contrast','Squared bin-index differences; symmetric counts merged across 13 directions; training-fold standardization.'),
      ('Postcontrast T1 mean','Dimensionless, unclipped percentile-scaled ROI mean; training-fold standardization.'),
      ('Postcontrast T1 standard deviation','Dimensionless; population SD (ddof=0); training-fold standardization.'),
      ('Postcontrast T1 entropy','Bits; Shannon entropy with 32 ROI-range bins; training-fold standardization.'),
      ('Postcontrast T1 GLCM contrast','Squared bin-index differences; symmetric counts merged across 13 directions; training-fold standardization.')]
    assert len(source)==len(descriptions)==13
    rows=[[r['变量'],desc,r['纳入模型'],processing] for r,(desc,processing) in zip(source,descriptions)]
    lock=json.loads((ROOT/'reports/ucsd_fusion/analysis_lock.json').read_text())
    for model,features in lock['model_features'].items():assert set(r[0] for r in rows if model in r[2].split())==set(features)
    return {'key':'TableS2','title':'Table S2. Predictor definitions and processing','headers':['Variable','Definition','Models','Processing and units'],'rows':rows,'notes':['M0: age and sex; M1: expanded clinical model; MRI: image features only; Fusion: clinical and MRI inputs. All learning of imputation and scaling parameters was confined to training folds.','The initial event could be initial surgery, another initial treatment, or diagnosis; only strictly negative source offsets were accepted as preceding the examination. Missing or nonnegative offsets were not treated as valid elapsed intervals.','MRI inputs used the union of positive supplied BraTS labels, without tissue-specific reinterpretation. The supplied spatial units were unknown; physical volumes and quantitative ADC were not included.']}

def document(title):
    doc=Document();sec=doc.sections[0];setup(sec,False)
    for name,size in [('Normal',12),('Title',16),('Heading 1',14),('Heading 2',12.5)]:
        st=doc.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
        rf=st.element.get_or_add_rPr().rFonts;rf.set(qn('w:eastAsia'),'Noto Serif CJK SC')
        for key in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:rf.attrib.pop(qn('w:'+key),None)
        st.paragraph_format.line_spacing=1.;st.paragraph_format.space_after=Pt(7)
    doc.styles['Normal'].paragraph_format.widow_control=True
    for name in ['Heading 1','Heading 2']:doc.styles[name].paragraph_format.keep_with_next=True
    for e in doc.styles.element.xpath('.//w:pBdr'):e.getparent().remove(e)
    doc.core_properties.title=title;doc.core_properties.author='Tianyu Feng'
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    return doc

def setup(sec,landscape):
    sec.orientation=WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    sec.page_width=Inches(11 if landscape else 8.5);sec.page_height=Inches(8.5 if landscape else 11)
    sec.top_margin=sec.bottom_margin=sec.left_margin=sec.right_margin=Inches(.79)
    sec.header_distance=sec.footer_distance=Inches(.35)

def lines(doc):
    for sec in doc.sections[:1]:
        e=OxmlElement('w:lnNumType');e.set(qn('w:countBy'),'1');e.set(qn('w:restart'),'continuous');e.set(qn('w:distance'),'180');sec._sectPr.append(e)

def paragraph(doc,s,chinese=False,keep_next=False):
    p=doc.add_paragraph(s);p.paragraph_format.keep_with_next=keep_next
    if chinese:
        for r in p.runs:r.font.size=Pt(11)
    return p

def add_abstract(doc,bilingual):
    doc.add_heading('Abstract',1)
    for p in ABSTRACT:
        q=paragraph(doc,'',keep_next=bilingual);q.add_run(p['label']+': ').bold=True;q.add_run(p['english'])
        if bilingual:paragraph(doc,p['chinese'],True)
    p=doc.add_paragraph();p.add_run('Keywords: ').bold=True;p.add_run('; '.join(KEYWORDS))

def add_table(doc,spec,landscape=False):
    sec=doc.add_section(WD_SECTION_START.NEW_PAGE);setup(sec,landscape)
    doc.add_heading(spec['title'],2)
    n=len(spec['headers']);width=9.42 if landscape else 6.92
    if spec['key']=='TableS2':widths=[1.8,2.0,1.0,4.62]
    elif n==4:widths=[2.4]+[(width-2.4)/3]*3
    else:widths=[1.35]+[(width-1.35)/(n-1)]*(n-1)
    t=doc.add_table(rows=1,cols=n);t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    for col,w in zip(t.columns,widths):col.width=Inches(w)
    for cell,label,w in zip(t.rows[0].cells,spec['headers'],widths):cell.text=label;cell.width=Inches(w)
    for row in spec['rows']:
        for cell,value,w in zip(t.add_row().cells,row,widths):cell.text=str(value);cell.width=Inches(w)
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+side)
        for k,v in [('val','single'),('sz','4'),('color','D9D9D9')]:e.set(qn('w:'+k),v)
        borders.append(e)
    t._tbl.tblPr.append(borders)
    for i,row in enumerate(t.rows):
        pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
        if i==0:pr.append(OxmlElement('w:tblHeader'))
        for cell in row.cells:
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if i==0:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'EEEEEE');cell._tc.get_or_add_tcPr().append(shade)
            for p in cell.paragraphs:
                p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1.
                for run in p.runs:run.font.size=Pt(10);run.font.bold=i==0
    for note in spec['notes']:
        p=paragraph(doc,note)
        for run in p.runs:run.font.size=Pt(10)

def add_figure(doc,key,fig,landscape):
    sec=doc.add_section(WD_SECTION_START.NEW_PAGE);setup(sec,landscape)
    width=9.2 if landscape else 6.8
    doc.add_heading(key,2)
    doc.add_picture(str(ROOT/fig['path']),width=Inches(width))
    p=paragraph(doc,fig['caption']);p.paragraph_format.keep_together=True
    for run in p.runs:run.font.size=Pt(10.5)

def build():
    OUT.mkdir(exist_ok=True,parents=True);REPORT.mkdir(exist_ok=True,parents=True)
    paths,sections,oldmap,refs,numbering=load_sources();eq,tables,figures=objects(sections);tables['TableS2']=table_s2()
    previous=sections[0]['source_audit']['frozen_file_sha256'].copy()
    previous.update(json.loads((ROOT/'reports/ucsd_manuscript_step54/artifact_verification.json').read_text())['sha256'])
    for p in paths+[ROOT/d['docx'] for d in sections]+[REPORT/'abstract_content.json']:
        key=str(p.relative_to(ROOT))
        if key not in previous:previous[key]=sha(p)
    for key,h in previous.items():assert sha(ROOT/key)==h,key
    paragraph_records=[]
    for d in sections:
        for item in d['paragraphs']:
            paragraph_records.append(dict(id=item['id'],english=renumber(item['english'],oldmap,numbering),chinese=renumber(item['chinese'],oldmap,numbering),citation_ids=item['citation_ids']))
    assert len(paragraph_records)==47 and len({x['id'] for x in paragraph_records})==47
    assert sum(wc(p['english']) for p in ABSTRACT)==247
    outputs=[]
    abstractdoc=document('Abstract');abstractdoc.add_paragraph(TITLE,style='Title');add_abstract(abstractdoc,True)
    p=OUT/'UCSD_Abstract_EN_ZH.docx';abstractdoc.save(p);outputs.append(p)
    (OUT/'UCSD_Abstract_EN.txt').write_text('\n\n'.join(p['label']+'\n'+p['english'] for p in ABSTRACT)+'\n\nKeywords: '+'; '.join(KEYWORDS)+'\n')
    for bilingual,filename in [(True,'UCSD_Manuscript_Integrated_EN_ZH.docx'),(False,'UCSD_Manuscript_Integrated_EN.docx')]:
        doc=document(TITLE);doc.add_paragraph(TITLE,style='Title');add_abstract(doc,bilingual)
        index=0
        for d in sections:
            h=d['subsection']
            if d['stage']==23:
                doc.add_heading('2 Materials and methods',1)
            elif d['stage']==33:
                doc.add_heading('3 Results',1)
            elif d['stage']==41:
                doc.add_heading('4 Discussion',1)
            if d['stage'] in [54,53]:
                p=doc.add_heading(h,1);p.paragraph_format.page_break_before=d['stage']==54
            else:doc.add_heading(h,2)
            for item in d['paragraphs']:
                rec=paragraph_records[index];index+=1;assert rec['id']==item['id']
                paragraph(doc,rec['english'],keep_next=bilingual)
                if bilingual:paragraph(doc,rec['chinese'],True)
                for obj in eq.get(item['id'],[]):
                    obj=deepcopy(obj)
                    for br in obj.xpath('.//w:pageBreakBefore'):br.getparent().remove(br)
                    doc.element.body.insert(len(doc.element.body)-1,obj)
        p=doc.add_heading('References',1);p.paragraph_format.page_break_before=True
        for rid,num in numbering.items():
            p=paragraph(doc,str(num)+'. '+refs[rid]);p.paragraph_format.keep_together=True
        for key in ['Table1','Table2','Table3']:add_table(doc,tables[key])
        for key in ['Figure 1','Figure 2','Figure 3']:add_figure(doc,key,figures[key],key!='Figure 1')
        for e in [*doc.styles.element.xpath('.//w:pBdr'),*doc.element.xpath('.//w:pBdr')]:e.getparent().remove(e)
        lines(doc)
        endmatter=False
        for para in doc.paragraphs:
            if para.text==tables['Table1']['title']:endmatter=True
            if endmatter:para._p.get_or_add_pPr().append(OxmlElement('w:suppressLineNumbers'))
        p=OUT/filename;doc.save(p);outputs.append(p)
    supp=document('Supplementary material');supp.add_paragraph('Supplementary material',style='Title');supp.add_paragraph(TITLE)
    # Avoid a separate title-only page: the first table shares this first section.
    for key in ['TableS1','TableS2','TableS3','TableS4','TableS5A','TableS5B','TableS6','TableS7']:
        add_table(supp,tables[key],key=='TableS2' or len(tables[key]['headers'])>5)
    for key in ['Figure S1','Figure S2']:add_figure(supp,key,figures[key],True)
    # Remove the initial title-only section; retain the title in document metadata and filename.
    body=supp.element.body
    for _ in range(3):
        if len(body) and body[0].tag==qn('w:p'):body.remove(body[0])
    # Restore a page-number footer on the new first section after removing the title-only section.
    supp.sections[0].footer.is_linked_to_previous=False
    fp=supp.sections[0].footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');fp._p.append(fld)
    p=OUT/'UCSD_Supplementary_Material_EN.docx';supp.save(p);outputs.append(p)
    with (OUT/'TableS2_EN.csv').open('w') as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(tables['TableS2']['headers']);w.writerows(tables['TableS2']['rows'])
    crosswalk=[{'old':old,'new':numbering[rid],'reference_id':rid} for old,rid in oldmap.items() if rid in numbering]
    payload={'stage':55,'date':'2026-10-30','title':TITLE,'abstract_paragraphs':ABSTRACT,'abstract_english_words':247,'keywords':KEYWORDS,'main_paragraphs':paragraph_records,'main_english_words':8200,'total_english_narrative_including_abstract':8447,'reference_numbering':numbering,'citation_crosswalk':crosswalk,'references':[{'number':num,'id':rid,'citation':refs[rid]} for rid,num in numbering.items()],
      'tables':tables,'figures':figures,'source_files_sha256':previous,'native_equation_group_numbers':list(range(1,11)),
      'equation_objects_sha256':[hashlib.sha256(canonical(obj)).hexdigest() for group in eq.values() for obj in group],
      'outputs':{str(p.relative_to(ROOT)):sha(p) for p in outputs},'declarations_and_acknowledgments_omitted_by_user':True,'author_affiliations_not_invented':True,'existing_narrative_changes':'Only citation numbers; no wording edits in the 47 confirmed narrative paragraphs','models_refitted':0,'new_bootstrap_draws':0,'new_hypothesis_tests':0}
    (REPORT/'assembly_receipt.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'outputs':list(payload['outputs']),'abstract_words':247,'main_words':8200,'native_equations':10,'references':25,'editable_tables':11,'figures':5,'frozen_files':len(previous)}))

def abstract_data_audit():
    import pandas as pd
    m=json.loads((ROOT/'reports/ucsd_fusion/metrics.json').read_text())
    st=json.loads((ROOT/'reports/ucsd_stability/metrics.json').read_text());single=st['single_scan']
    assert (m['scans'],m['source_patients'],m['tumor_scans'],m['treatment_change_scans'])==(182,135,141,41)
    pairs={p['metric']:p for p in m['paired_comparisons'] if p['comparison']=='Fusion_minus_M1'}
    values={'primary_fusion_auc':m['metrics']['Fusion']['roc_auc'],'clinical_auc':m['metrics']['M1']['roc_auc'],'mri_auc':m['metrics']['MRI']['roc_auc'],'primary_increment':pairs['roc_auc']['difference'],'primary_lower':pairs['roc_auc']['lower'],'primary_upper':pairs['roc_auc']['upper'],'single_fusion_auc':single['metrics']['Fusion']['roc_auc'],'single_increment':single['paired_differences']['roc_auc'],'single_lower':single['bootstrap_95ci']['Fusion_minus_M1__roc_auc']['lower'],'single_upper':single['bootstrap_95ci']['Fusion_minus_M1__roc_auc']['upper'],'calibration_slope':m['calibration']['Fusion']['calibration_slope']}
    displayed=['0.782','0.672','0.762','0.110','0.021','0.214','0.730','0.120','-0.015','0.252','0.667']
    assert [f'{x:.3f}' for x in values.values()]==displayed
    assert all(x in ABSTRACT[2]['english'] for x in displayed)
    oof=pd.read_csv(ROOT/'data/processed/ucsd_fusion_oof.csv');assert len(oof)==182 and oof['validation_group'].nunique()==135 and oof['validation_fold'].nunique()==5
    pred=oof['Fusion_oof_probability'].ge(.5);label=oof['tumor_label'].eq(1)
    assert (int((pred&label).sum()),int((~pred&~label).sum()),int(label.sum()),int((~label).sum()))==(130,12,141,41)
    assert m['bootstrap_attempts']==2000 and m['bootstrap_valid']==2000 and not m['bootstrap_models_refitted']
    rep=pd.read_csv(ROOT/'reports/ucsd_stability/repeated_paired_differences.csv');a=rep[(rep.comparison=='Fusion_minus_M1')&(rep.metric=='roc_auc')]
    assert len(a)==20 and (a.difference>0).all()
    assert all(pairs[k]['lower']<0<pairs[k]['upper'] for k in ['brier','log_loss'])
    assert single['bootstrap_95ci']['Fusion_minus_M1__roc_auc']['lower']<0<single['bootstrap_95ci']['Fusion_minus_M1__roc_auc']['upper']
    lock=json.loads((ROOT/'reports/ucsd_fusion/analysis_lock.json').read_text());assert {k:len(v) for k,v in lock['model_features'].items()}=={'M0':2,'M1':5,'MRI':8,'Fusion':13}
    return {'saved_full_precision_values':values,'displayed_values':displayed,'OOF_counts_and_five_folds_checked':True,'repeated_positive_increments_checked':20,'conditional_fixed_probability_bootstrap':True,'probability_error_intervals_include_zero':True,'models_refitted':0}

def verify():
    from pypdf import PdfReader
    d=json.loads((REPORT/'assembly_receipt.json').read_text());paths,sections,oldmap,refs,numbering=load_sources();eq,_,_=objects(sections)
    for rel,h in d['source_files_sha256'].items():assert sha(ROOT/rel)==h,rel
    sourceeq=[canonical(obj) for group in eq.values() for obj in group]
    pages={};totals={}
    for rel,h in d['outputs'].items():
        path=ROOT/rel;assert sha(path)==h;doc=Document(path);texts=[p.text for p in doc.paragraphs]
        englishonly=path.name.endswith('_EN.docx')
        text='\n'.join(texts+[cell.text for t in doc.tables for row in t.rows for cell in row.cells])
        if englishonly:assert not re.search(r'[\u3400-\u9fff，。；：（）【】、]',text),path.name
        ismain='Integrated' in path.name;isabstract='Abstract' in path.name
        if ismain or isabstract:
            for p in ABSTRACT:assert p['label']+': '+p['english'] in texts
            if not englishonly:
                for p in ABSTRACT:assert texts.index(p['chinese'])==texts.index(p['label']+': '+p['english'])+1
            assert not re.search(r'\([0-9,]+\)',ABSTRACT[0]['english'])
        if ismain:
            for p in d['main_paragraphs']:
                assert texts.count(p['english'])==1,(path.name,p['id'])
                if not englishonly:assert texts.index(p['chinese'])==texts.index(p['english'])+1
            assert len(doc.tables)==3
            for ref in d['references']:assert str(ref['number'])+'. '+ref['citation'] in texts
            assert len(doc.element.xpath('//m:oMath'))==10
            forms=[canonical(p) for p in doc.element.body if p.xpath('.//m:oMath')]
            # Paragraph properties may be normalized, but formula XML and displayed number are preserved.
            for a,b in zip(forms,sourceeq):
                xa=etree.fromstring(a);xb=etree.fromstring(b)
                assert [etree.tostring(x,method='c14n',exclusive=True) for x in xa.xpath('.//m:oMath',namespaces=NS)]==[etree.tostring(x,method='c14n',exclusive=True) for x in xb.xpath('.//m:oMath',namespaces=NS)]
                assert ''.join(xa.xpath('.//w:t/text()',namespaces=NS))==''.join(xb.xpath('.//w:t/text()',namespaces=NS))
            assert doc.sections[0]._sectPr.find(qn('w:lnNumType')) is not None
            assert all(s._sectPr.find(qn('w:lnNumType')) is None for s in doc.sections[1:])
            for t,key in zip(doc.tables,['Table1','Table2','Table3']):assert [[c.text for c in row.cells] for row in t.rows]==[d['tables'][key]['headers'],*d['tables'][key]['rows']]
            assert 'Data availability' not in texts and 'Acknowledgments' not in texts
        if 'Supplementary' in path.name:
            keys=['TableS1','TableS2','TableS3','TableS4','TableS5A','TableS5B','TableS6','TableS7'];assert len(doc.tables)==8
            for t,key in zip(doc.tables,keys):assert [[c.text for c in row.cells] for row in t.rows]==[d['tables'][key]['headers'],*d['tables'][key]['rows']]
        expectedfigs=['Figure 1','Figure 2','Figure 3'] if ismain else ['Figure S1','Figure S2'] if 'Supplementary' in path.name else []
        with zipfile.ZipFile(path) as z:
            media=[hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')]
            assert sorted(media)==sorted(d['figures'][k]['sha256'] for k in expectedfigs),(path.name,len(media))
        pdf=OUT/(path.stem+'_render')/(path.stem+'.pdf');p=PdfReader(pdf);pages[path.name]=len(p.pages)
        assert len(p.pages)>0
        totals[path.name]={'pages':len(p.pages),'editable_tables':len(doc.tables),'native_equation_groups':len(doc.element.xpath('//m:oMath')),'embedded_figures':len(expectedfigs),'english_only':englishonly}
    assert [ref['number'] for ref in d['references']]==list(range(1,26))
    ordered=[]
    for p in d['main_paragraphs']:
        for group in re.findall(r'\(([0-9]+(?:\s*,\s*[0-9]+)*)\)',p['english']):
            for number in map(int,group.split(',')):
                if number not in ordered:ordered.append(number)
    assert ordered==list(range(1,26))
    assert sum(wc(p['english']) for p in d['main_paragraphs'])==8200 and sum(wc(p['english']) for p in ABSTRACT)==247
    assert all(not x['citation_ids'] for x in ABSTRACT)
    v={'success':True,'abstract_saved_data_audit':abstract_data_audit(),'stage':55,'date':'2026-10-30','abstract_english_words':247,'main_english_words':8200,'all51_narrative_units_present':True,'translated_units':51,'unique_references':25,'references_in_global_first_appearance_order':True,'confirmed_main_text_changes_only_citation_numbers':True,'prior_files_unchanged':len(d['source_files_sha256']),'editable_tables_total':11,'TableS2_translated_and_model_membership_checked':True,'source_figure_bytes_unchanged':5,'native_formula_groups_preserved_per_main_file':10,'document_checks':totals,'declarations_and_acknowledgments_omitted_by_user':True,'author_affiliations_not_invented':True,'models_refitted':0,'new_bootstrap_draws':0,'new_hypothesis_tests':0,'sha256':{str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file()}}
    (REPORT/'artifact_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps(v,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args();verify() if args.verify else build()
