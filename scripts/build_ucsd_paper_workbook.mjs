import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const outputDir=path.join(root,'outputs/ucsd-paper-materials-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_paper_materials/table_package.json'),'utf8'));
const datasets=Object.fromEntries(d.tables.map(t=>[t.key,t]));datasets.BaselineNumbers=d.baseline_numeric;
const wb=Workbook.create(),sheets=Object.fromEntries(['Index',...Object.keys(datasets)].map(n=>[n,wb.worksheets.add(n)]));
const head={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:46};
for(const [name,data]of Object.entries(datasets)){
 const sh=sheets[name],n=data.rows.length+1,m=data.headers.length;
 sh.getRangeByIndexes(0,0,n,m).values=[data.headers,...data.rows];sh.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:30,verticalAlignment:'center'};
 data.headers.forEach((key,j)=>{
  const col=sh.getRangeByIndexes(0,j,n,1);col.format.columnWidth=name==='TableS2'?(j===0?33:j===1?26:j===2?25:90):j===0?40:/cohort|statistic|variable/.test(key)?32:Math.max(19,Math.min(29,key.length));
  const numeric=data.rows.some(r=>typeof r[j]==='number');
  col.setNumberFormat(numeric?(/correct|total|repeats|denominator|patient_count|observed_n|^count$/.test(key)?'#,##0':/Balanced|accuracy/.test(key)?'0.0%':'0.0000'):'@');
 });
 if(['Table1','TableS1'].includes(name)){
  sh.getRangeByIndexes(1,1,2,m-1).setNumberFormat('0');sh.getRangeByIndexes(2,0,n-2,m).format.rowHeight=30;
 }
 sh.getRangeByIndexes(0,0,1,m).format=head;sh.tables.add(sh.getRangeByIndexes(0,0,n,m),true,'Paper'+name);sh.showGridLines=false;
 sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(1);
 if(data.notes){
  const start=n+2;data.notes.forEach((note,i)=>{const r=sh.getRangeByIndexes(start+i,0,1,1);r.values=[['注：'+note]];r.format.font={name:'Arial',size:10,color:'#536474'};});
 }
}
const sh=sheets.Index;sh.showGridLines=false;sh.tabColor='#35556D';sh.getRange('B2').values=[['胶质瘤研究表图索引']];sh.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
sh.getRange('B4:D4').values=[['表编号','内容','数据行数']];sh.getRange('B5:D15').values=d.tables.map(t=>[t.key,t.title,null]);
for(let i=0;i<d.tables.length;i++)sh.getRange(`D${i+5}`).formulas=[[`=COUNTA('${d.tables[i].key}'!A2:A${d.tables[i].rows.length+1})`]];
sh.getRange('B18:D18').values=[['主结果与敏感性','AUC或数量','说明']];
sh.getRange('B19:D22').values=[['主分析融合AUC',null,'第18步固定患者分组OOF，未改选最佳重复'],['单扫描融合AUC',null,'不同扫描人群，不与182条主分析直接配对比较'],['单扫描治疗改变正确识别',null,'分母为22次治疗改变'],['原影像队列扫描数',null,'扫描数不是患者数']];
sh.getRange('C19:C22').formulas=[["='Table2'!B5"],["='TableS6'!B5"],["='TableS6'!G5"],["='Table1'!B2"]];
sh.getRange('B25').values=[['基线组合显示值的原始数值见BaselineNumbers页；没有新增模型拟合或显著性检验。']];
sh.getRange('B26').values=[['原主分析、边界、20套重复与单扫描结果全部保留；论文正文等待新的写作指示。']];
sh.getRange('B28').values=[['数据来源：UCSD-PTGBM，DOI 10.7937/fwv2-dt74；公开镜像github.com/data-nih/tcia/releases。']];
sh.getRange('B4:D28').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:30,verticalAlignment:'center'};
sh.getRange('B4:B28').format.columnWidth=38;sh.getRange('C4:C28').format.columnWidth=65;sh.getRange('D4:D28').format.columnWidth=70;
for(const r of ['B4:D4','B18:D18'])sh.getRange(r).format=head;
sh.getRange('C19:C20').setNumberFormat('0.0000');sh.getRange('C21:C22').setNumberFormat('0');sh.getRange('D5:D15').setNumberFormat('0');
wb.recalculate();
if(Math.abs(sh.getRange('C19').values[0][0]-.781871648503719)>1e-12||sh.getRange('C21').values[0][0]!==2||sh.getRange('C22').values[0][0]!==182)throw new Error('Paper summary mismatch');
const cell=sheets.Table2.getRange('B5'),old=cell.values[0][0];cell.values=[[.123]];wb.recalculate();if(sh.getRange('C19').values[0][0]!==.123)throw new Error('Linked result does not update');cell.values=[[old]];wb.recalculate();
await fs.mkdir(outputDir,{recursive:true});await fs.writeFile(path.join(outputDir,'summary.inspect.ndjson'),(await wb.inspect({kind:'table',range:'Index!B4:D22',include:'values,formulas',tableMaxRows:19,tableMaxCols:3,maxChars:3500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
for(const name of ['Index',...Object.keys(datasets)]){
 const range=name==='Index'?'B2:D28':`${name==='BaselineNumbers'?'A1:G7':name==='TableS2'?'A1:D6':name==='Table1'||name==='TableS1'?'A1:D11':'A1:H6'}`;
 const blob=await wb.render({sheetName:name,range,scale:1.05,format:'png'});await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_Paper_Numeric_Tables.xlsx'));
console.log(JSON.stringify({exported:true,table_count:d.tables.length,sheets:Object.keys(sheets),linked_summary_recalculation_verified:true}));
