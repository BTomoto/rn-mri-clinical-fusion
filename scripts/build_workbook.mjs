import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root=process.env.RN_PROJECT_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outputDir=path.join(root, 'outputs/research-data');
await fs.mkdir(outputDir,{recursive:true});
const input=JSON.parse(await fs.readFile(path.join(root,'data/metadata/workbook_input.json'),'utf8'));
const wb=Workbook.create();
const overview=wb.worksheets.add('Overview');
overview.showGridLines=false;
overview.tabColor='#244969';
overview.getRange('B2').values=[['公开MRI与临床数据工作簿']];
overview.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
overview.getRange('B4:D4').values=[['指标','数值','定义与当前状态']];
const rows=[
 ['患者数',null,'公开临床表中的唯一患者编号'],
 ['病灶记录数',null,'患者—病灶组合；不等于全部影像病灶数'],
 ['有脑坏死时间的病灶',null,'来源字段存在数值；尚未逐例核验诊断依据'],
 ['脑坏死状态未知的病灶',null,'来源时间空白；不能当作阴性对照'],
 ['原始影像患者—日期组合',null,'按原始DICOM文件目录去重'],
 ['原始DICOM序列数',null,'具有DICOM切片的目录组合'],
 ['基线时间匹配候选病灶',null,'首次SRS前30天内有患者级影像目录'],
 ['最终确认纳入病灶',null,'需完成结局核验、病灶定位和影像质控'],
];
overview.getRange('B5:D12').values=rows;
overview.getRange('B15:D15').values=[['研究阶段','数据整理与可行性核验','尚未训练临床风险预测模型']];
overview.getRange('B17:D17').values=[['时间说明','1900-01-01为去标识基准','相对天数保留；并非实际检查年份']];
overview.getRange('B19:D19').values=[['影像存储','Excel保存索引和数值','MRI体素与分割文件单独保存']];
overview.getRange('B21:D21').values=[['后续审核','OutcomeReview为人工核验工作表','空白结局不会自动转成0']];
overview.getRange('B23:D25').values=[['已下载DICOM切片',null,'成员CRC32验证；另外保存SHA256清单'],['已下载患者—日期组合',null,'保存所选基线与早期检查的全部可用序列'],['原始MRI体积（GB）',null,'解压后十进制GB；MRI文件单独归档']];
overview.getRange('B2:D25').format.font.name='Arial';
overview.getRange('B4:D25').format.font.size=11;
overview.getRange('B4:D4').format={fill:'#244969',font:{color:'#FFFFFF',bold:true},rowHeight:30};
overview.getRange('B5:D12').format.rowHeight=32;
overview.getRange('B15:D21').format.rowHeight=30;
overview.getRange('B23:D25').format.rowHeight=30;
overview.getRange('B2:B25').format.columnWidth=32;
overview.getRange('C2:C25').format.columnWidth=32;
overview.getRange('D2:D25').format.columnWidth=64;
overview.getRange('C5:C12').setNumberFormat('#,##0');

function colLetter(n){let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;}
for(const spec of input.sheets){
 const s=wb.worksheets.add(spec.name);s.showGridLines=false;
 const n=spec.rows.length+1,m=spec.headers.length,last=colLetter(m);
 s.getRangeByIndexes(0,0,n,m).values=[spec.headers,...spec.rows];
 const used=s.getRange(`A1:${last}${n}`);
 used.format.font={name:'Arial',size:10,color:'#263747'};
 used.format.verticalAlignment='center';
 used.format.rowHeight=23;
 used.setNumberFormat('0.0000');
 const header=s.getRange(`A1:${last}1`);
 header.format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:48,verticalAlignment:'center',horizontalAlignment:'center'};
 for(let j=0;j<m;j++){
  const c=spec.headers[j], range=s.getRangeByIndexes(0,j,n,1);
  const values=spec.rows.map(r=>r[j]).filter(v=>v!==null);
  const text=values.some(v=>typeof v==='string');
  const width=/detail|definition|missing_rule|source_url|evidence_source|review_notes/.test(c)?70:
      /sha256|series_name|Image|Mask|filename/.test(c)?52:
      /status|reference_standard|source_volume_unit/.test(c)?38:
      Math.min(31,Math.max(17,c.length*.76));
  range.format.columnWidth=width;
  if(text){
   range.setNumberFormat('@');s.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment='left';
   const maxChars=Math.max(...values.map(v=>String(v).length));
   if(maxChars>width*1.3){
    s.getRangeByIndexes(1,j,n-1,1).format.wrapText=true;
    s.getRange(`A2:${last}${n}`).format.rowHeight=46;
   }
  } else if(values.every(v=>Number.isInteger(v))) range.setNumberFormat('0');
  if(/_id$|date_code|Patient|Timepoint/.test(c)){range.setNumberFormat('@');}
  if(/_day$|_days$|_count$|_files$|^lesion_id$|^final_eligible$|complete$|hint$|adjudicated$|^use_for_model$/.test(c)&&!text)range.setNumberFormat('0');
 }
 header.format.horizontalAlignment='center';
 s.tables.add(`A1:${last}${n}`,true,`${spec.name}Table`);
 s.freezePanes.freezeRows(1);
 if(m>7)s.freezePanes.freezeColumns(Math.min(2,m));
 if(spec.name==='OutcomeReview'){
  s.tabColor='#A67824';
  const h=spec.headers;
  for(const key of ['adjudicated_rn_event','adjudicated_rn_time_day','last_event_free_followup_day','reference_standard','evidence_source','review_notes','review_status']){
   const j=h.indexOf(key);s.getRangeByIndexes(1,j,n-1,1).format.fill='#FFF4D6';
  }
  const rj=h.indexOf('review_status');s.getRangeByIndexes(1,rj,n-1,1).dataValidation={rule:{type:'list',values:['pending','verified_event','verified_event_free','exclude','uncertain']}};
  const ej=h.indexOf('adjudicated_rn_event');s.getRangeByIndexes(1,ej,n-1,1).dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:1}};
 }
 if(spec.name==='Lesions'){
  const j=spec.headers.indexOf('rn_status');s.getRangeByIndexes(1,j,n-1,1).conditionalFormats.add('containsText',{text:'unknown',format:{fill:'#FFF0D9'}});
 }
}
overview.getRange('C5').formulas=[[`=COUNTA(Patients!A2:A76)`]];
overview.getRange('C6').formulas=[[`=COUNTA(Lesions!C2:C161)`]];
overview.getRange('C7').formulas=[[`=COUNT(Lesions!N2:N161)`]];
overview.getRange('C8').formulas=[[`=COUNTIFS(Lesions!O2:O161,"unknown")`]];
overview.getRange('C9').formulas=[[`=COUNTA(ImageStudies!A2:A636)`]];
overview.getRange('C10').formulas=[[`=COUNTA(ImageSeries!A2:A3112)`]];
overview.getRange('C11').formulas=[[`=COUNTA(BaselineMatches!A2:A91)`]];
overview.getRange('C12').formulas=[[`=SUM(Lesions!AB2:AB161)`]];
overview.getRange('C23').formulas=[[`=SUM(ImageDownloads!C2:C108)`]];
overview.getRange('C24').formulas=[[`=COUNTA(ImageDownloads!A2:A108)`]];
overview.getRange('C25').formulas=[[`=SUM(ImageDownloads!D2:D108)/1000000000`]];
overview.getRange('C23:C24').setNumberFormat('#,##0');
overview.getRange('C25').setNumberFormat('0.00');
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Overview!B4:D12',include:'values,formulas',tableMaxRows:12,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20}})).ndjson);
for(const name of ['Overview',...input.sheets.map(x=>x.name)]){
 const spec=input.sheets.find(x=>x.name===name);
 const range=name==='Overview'?'B2:D25':`A1:${colLetter(Math.min(6,spec.headers.length))}${Math.min(5,spec.rows.length+1)}`;
 const blob=await wb.render({sheetName:name,range,scale:1.3,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(path.join(outputDir,'RN_Public_Data.xlsx'));
console.log('EXPORTED',path.join(outputDir,'RN_Public_Data.xlsx'));
