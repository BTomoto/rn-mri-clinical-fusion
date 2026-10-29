import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const out=path.join(root,'outputs/ucsd-manuscript-step23-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_manuscript_step23/reference_library.json'),'utf8'));
const wb=Workbook.create();const summary=wb.worksheets.add('Summary'),refs=wb.worksheets.add('References'),evidence=wb.worksheets.add('Evidence');
const header={fill:'#294E66',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:40,verticalAlignment:'center'};
function table(sh,headers,rows,widths,height,name){
 const n=rows.length+1,m=headers.length;sh.getRangeByIndexes(0,0,n,m).values=[headers,...rows];
 sh.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#243744'},wrapText:true,verticalAlignment:'center',rowHeight:height};
 widths.forEach((w,j)=>{sh.getRangeByIndexes(0,j,n,1).format.columnWidth=w;sh.getRangeByIndexes(0,j,n,1).setNumberFormat('@');});
 sh.getRangeByIndexes(0,0,1,m).format=header;sh.tables.add(sh.getRangeByIndexes(0,0,n,m),true,name);
 sh.showGridLines=false;sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(1);
}
table(refs,['ID','First author','Title','Journal','DOI','PMID','Language','Journal year','Eligibility year','English flag','Recent 5 years','Recent 3 years','Source URL','DOI verification','Electronic dates'],d.references.map(r=>[r.id,r.first_author,r.title,r.journal,r.doi||'',r.pmid||'',r.language,r.publication_year,r.eligibility_year,r.english_flag,null,null,r.source_url,r.doi_verification,(r.electronic_dates||[]).join('; ')]),[9,22,75,23,34,15,13,15,17,15,18,18,57,30,26],100,'CandidateReferences');
refs.getRange('H2:L41').setNumberFormat('0');
for(let i=2;i<=41;i++){
 refs.getRange(`K${i}`).formulas=[[`=IF(AND(I${i}>='Summary'!$C$18,I${i}<='Summary'!$C$17,J${i}=1),1,0)`]];
 refs.getRange(`L${i}`).formulas=[[`=IF(AND(I${i}>='Summary'!$C$19,I${i}<='Summary'!$C$17,J${i}=1),1,0)`]];
}
table(evidence,['ID','Role','Supported use','Limitations / cautions','V2 outline locations','Reading level','Cited in section 2.1'],d.references.map(r=>[r.id,r.role,r.support,r.limitation,r.outline_locations,r.read_level,r.in_current_section]),[9,26,65,70,26,49,21],112,'EvidenceMapping');
evidence.getRange('G2:G41').setNumberFormat('0');
summary.showGridLines=false;summary.tabColor='#294E66';summary.getRange('B2').values=[['Candidate reference and evidence library']];summary.getRange('B2').format.font={name:'Arial',size:17,bold:true,color:'#294E66'};
summary.getRange('B4:D4').values=[['Metric','Current value','Interpretation']];
summary.getRange('B5:D13').values=[['Candidate references',null,'Candidate pool, not the final manuscript citation list'],['English-language references',null,'Language checked against source records'],['Recent 5 years',null,'English; 2022-2026'],['Recent 5-year share',null,'Collaborator requirement: more than 90%'],['Recent 3 years',null,'English; 2024-2026'],['Recent 3-year share',null,'Collaborator requirement: majority'],['Cited in section 2.1',null,'Final numbering will be rebuilt after Introduction'],['PubMed DOI records verified',39,'JMLR 2011 is verified on its publisher page'],['Secondary Crossref matches',30,'Nine secondary checks rate-limited; primary records verified']];
summary.getRange('C5:C11').formulas=[["=COUNTA('References'!A2:A41)"],["=SUM('References'!J2:J41)"],["=SUM('References'!K2:K41)"],['=C7/C5'],["=SUM('References'!L2:L41)"],['=C9/C5'],["=SUM('Evidence'!G2:G41)"]];
summary.getRange('B16:D16').values=[['Calendar controls','Year','Rule']];
summary.getRange('B17:D19').values=[['As-of year',2026,'As-of date: 2026-10-29'],['5-year lower bound',null,'Inclusive calendar-year window'],['3-year lower bound',null,'Inclusive calendar-year window']];
summary.getRange('C18:C19').formulas=[['=C17-4'],['=C17-2']];
const notes=[
 'Eligibility uses the earliest explicit online or journal year; a year embedded in a DOI is not a publication date.',
 'Focused topic and methods screening; not a systematic review or 40 completed full-text reviews.',
 'At least 25 final references are required. Recheck both recency shares after final citation selection.',
 'S19 uses the same UCSD parent collection. It is related work, not independent external validation.',
 'Evidence records separate abstract screening, relevant full-text review and official checklist review.',
 'Source records, DOI links, publication dates and reading levels are preserved for each reference.'
];
notes.forEach((n,i)=>{summary.getRange(`B${22+i}:D${22+i}`).merge();summary.getRange(`B${22+i}`).values=[[n]];});
summary.getRange('B4:D27').format={font:{name:'Arial',size:11,color:'#243744'},rowHeight:43,wrapText:true,verticalAlignment:'center'};
summary.getRange('B4:B27').format.columnWidth=33;summary.getRange('C4:C27').format.columnWidth=18;summary.getRange('D4:D27').format.columnWidth=67;
for(const range of ['B4:D4','B16:D16'])summary.getRange(range).format=header;
summary.getRange('C5:C19').setNumberFormat('0');summary.getRange('C8').setNumberFormat('0.0%');summary.getRange('C10').setNumberFormat('0.0%');
wb.recalculate();
const values=()=>[5,6,7,8,9,10,11].map(r=>summary.getRange(`C${r}`).values[0][0]);
if(JSON.stringify(values())!==JSON.stringify([40,40,37,.925,31,.775,3]))throw new Error('Reference counts mismatch');
const year=refs.getRange('I2').values[0][0];refs.getRange('I2').values=[[2021]];wb.recalculate();if(summary.getRange('C7').values[0][0]!==36||summary.getRange('C9').values[0][0]!==30)throw new Error('Recency formulas not linked');refs.getRange('I2').values=[[year]];wb.recalculate();
await fs.mkdir(out,{recursive:true});
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},maxChars:1200});console.log(errors.ndjson);
for(const [sheet,range,label] of [['Summary','B2:D27','Summary'],['References','A1:D7','References'],['References','H1:L8','Eligibility'],['Evidence','A1:F5','Evidence'],['Evidence','A19:F22','Evidence19']]){
 const b=await wb.render({sheetName:sheet,range,scale:1,format:'png'});await fs.writeFile(path.join(out,`preview_${label}.png`),new Uint8Array(await b.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,'UCSD_Reference_Evidence_Library.xlsx'));
console.log(JSON.stringify({exported:true,sheets:3,counts:values(),formula_perturbation_verified:true}));
