import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root=process.env.RN_PROJECT_ROOT;
if(!root) throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/readiness-20261028');
const data=JSON.parse(await fs.readFile(path.join(root,'reports/readiness_workbook_input.json'),'utf8'));
await fs.mkdir(outputDir,{recursive:true});
const wb=Workbook.create();
const main=wb.worksheets.add('Summary');
const letters=n=>{let r='';while(n){n--;r=String.fromCharCode(65+n%26)+r;n=Math.floor(n/26);}return r;};
for(const spec of data.sheets){
 const s=wb.worksheets.add(spec.name),n=spec.rows.length+1,m=spec.headers.length;
 s.showGridLines=false;
 s.getRangeByIndexes(0,0,n,m).values=[spec.headers,...spec.rows];
 const body=s.getRangeByIndexes(0,0,n,m);
 body.format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:24,verticalAlignment:'center'};
 for(let j=0;j<m;j++){
  const key=spec.headers[j],r=s.getRangeByIndexes(0,j,n,1);
  r.format.columnWidth=/finding|endpoint_action|remaining_requirements/.test(key)?90:
    /sha256|file|url|evidence_location/.test(key)?64:
    /class|status|scope|standard|shape|spacing|Sequence|Description|Protocol/.test(key)?42:Math.max(18,Math.min(36,key.length*.8));
  const texts=spec.rows.some(row=>typeof row[j]==='string');
  r.setNumberFormat(texts?'@':/volume|difference|voxel_mm3|mask_total|morphology_total|radiomics_voxel/.test(key)?'0.00000':'0');
  s.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment=texts?'left':'right';
  if(texts && spec.name!=='Evidence' && spec.rows.some(row=>typeof row[j]==='string' && row[j].length>90)){
   s.getRangeByIndexes(1,j,n-1,1).format.wrapText=true;
   s.getRangeByIndexes(1,0,n-1,m).format.rowHeight=72;
  }
 }
 s.getRangeByIndexes(0,0,1,m).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:54,horizontalAlignment:'center',verticalAlignment:'center'};
 s.tables.add(`A1:${letters(m)}${n}`,true,`${spec.name}Table`);
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(1);
 if(spec.name==='Evidence'){
  s.getRange(`A2:${letters(m)}${n}`).format.wrapText=true;
  s.getRange(`A2:${letters(m)}${n}`).format.rowHeight=128;
  s.getRange(`A2:${letters(m)}${n}`).format.verticalAlignment='top';
 }
 if(spec.name==='OutcomeAudit'){
  for(const key of ['rn_after_death','index_srs_after_death']){
   const j=spec.headers.indexOf(key);
   s.getRangeByIndexes(1,j,n-1,1).conditionalFormats.add('cellIs',{operator:'equal',formula:'1',format:{fill:'#FFE2DA',font:{color:'#9C2F1C',bold:true}}});
  }
 }
}
main.showGridLines=false;main.tabColor='#244969';
main.getRange('B2').values=[['公开数据可分析性核查']];
main.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
main.getRange('B4:D4').values=[['指标','数值','解释']];
const outcome=data.sheets.find(s=>s.name==='OutcomeAudit');
const col=k=>letters(outcome.headers.indexOf(k)+1);
const span=k=>`OutcomeAudit!${col(k)}2:${col(k)}${outcome.rows.length+1}`;
const rows=[
 ['临床病灶记录',`=COUNTA(${span('lesion_key')})`,'75名患者的160条病灶记录'],
 ['数值型坏死时间',`=COUNT(${span('rn_time_day')})`,'事件时间有记录，逐例诊断依据仍待核实'],
 ['坏死结局未知',`=COUNTIFS(${span('rn_evidence_class')},"unknown")`,'空白及空格保持未知，不编码为0'],
 ['坏死早于或等于首次SRS',`=COUNTIFS(${span('rn_evidence_class')},"rn_at_or_before_index_srs")`,'需核查既往治疗史及时间字段'],
 ['坏死时间晚于死亡',`=SUM(${span('rn_after_death')})`,'保留原始值，标记时间冲突'],
 ['首次SRS晚于死亡',`=SUM(${span('index_srs_after_death')})`,'保留原始值，标记时间冲突'],
 ['治疗前30天影像目录候选',`=SUM(${span('baseline_directory_candidate')})`,'患者级目录匹配，目标病灶尚待定位'],
 ['窗口内有实际掩膜的病灶',`=SUM(${span('baseline_actual_mask_available')})`,'以掩膜日期及影像组学表交叉核对'],
 ['其中有数值型坏死时间',`=COUNTIFS(${span('baseline_actual_mask_available')},1,${span('rn_evidence_class')},"recorded_rn_after_index_srs")`,'具备部分基线特征，结局仍待核实'],
 ['可确认的阴性对照',`=SUM(${span('verified_non_event')})`,'有后续MRI不等于可确认无坏死'],
 ['已完成全部核验的病灶',`=SUM(${span('final_eligible')})`,'0表示核验未完成，不代表所有病例均被排除'],
 ['可读取的NIfTI掩膜',`=COUNTIFS(MaskFiles!F2:F${data.sheets.find(s=>s.name==='MaskFiles').rows.length+1},"readable")`,'结构检查通过仍不等于解剖定位正确'],
 ['DICOM抽样目录',`=COUNTA(DICOMSamples!A2:A${data.sheets.find(s=>s.name==='DICOMSamples').rows.length+1})`,'每个目录按ZIP排列抽取首尾文件'],
 ['DICOM抽样文件',`=SUM(DICOMSamples!F2:F${data.sheets.find(s=>s.name==='DICOMSamples').rows.length+1})`,'CRC及头信息检查，不是完整序列质控']
];
main.getRange(`B5:D${rows.length+4}`).values=rows.map(r=>[r[0],null,r[2]]);
main.getRange(`C5:C${rows.length+4}`).formulas=rows.map(r=>[r[1]]);
main.getRange('B21:D21').values=[['当前决定','暂不训练预测模型','优先解决可追溯的结局标签和基线分割']];
main.getRange('B23:D23').values=[['文献与文件的差异','论文39个，临床文件32个','缺少逐病灶对照表，差异尚未解释']];
main.getRange('B25:D25').values=[['核查日期','2026-10-28','原始临床表和既有主工作簿均保留']];
main.getRange('B4:D25').format.font={name:'Arial',size:11,color:'#263747'};
main.getRange('B4:D4').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:30};
main.getRange('B5:D25').format.rowHeight=32;
main.getRange('B2:B25').format.columnWidth=34;
main.getRange('C2:C25').format.columnWidth=30;
main.getRange('D2:D25').format.columnWidth=64;
main.getRange('C5:C18').setNumberFormat('#,##0');
main.getRange('C5:C18').format.horizontalAlignment='center';
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:D18',include:'values,formulas',tableMaxRows:16,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20}})).ndjson);
for(const name of ['Summary',...data.sheets.map(s=>s.name)]){
 const range=name==='Summary'?'B2:D26':name==='Evidence'?'A1:F3':name==='MaskFiles'?'A1:H5':name==='OutcomeAudit'?'A1:I5':'A1:H5';
 const b=await wb.render({sheetName:name,range,scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await b.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(outputDir,'RN_Readiness_Audit.xlsx'));
console.log('Exported RN_Readiness_Audit.xlsx');
