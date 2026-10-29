import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const outputDir=path.join(root,'outputs/ucsd-stability-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_stability_workbook_input.json'),'utf8'));
const names=['Summary',...Object.keys(d.datasets)],wb=Workbook.create(),sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const letter=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
const head={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:48};
function table(name,data){
 const sh=sheets[name],n=data.rows.length+1,m=data.headers.length;
 sh.getRangeByIndexes(0,0,n,m).values=[data.headers,...data.rows.map(r=>r.map(v=>typeof v==='boolean'?Number(v):v))];
 sh.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:26,verticalAlignment:'center'};
 data.headers.forEach((key,j)=>{
  const col=sh.getRangeByIndexes(0,j,n,1),vals=data.rows.map(r=>r[j]);
  col.format.columnWidth=/label_source|primary_diagnosis_raw|reason/.test(key)?90:/ID$|patient_id|validation_group/.test(key)?34:/comparison/.test(key)?42:Math.max(18,Math.min(29,key.length*.85));
  const numeric=vals.some(v=>typeof v==='number'||typeof v==='boolean');
  const integer=/^(repeat|seed|validation_fold|tumor_label|selected|session_number|tn|fp|fn|tp|age_years|sex_male|other_treatment_prior|initial_event_missing|complete|failed_fold_model_records)$/.test(key)||/prediction_0_5$/.test(key);
  col.setNumberFormat(numeric?(integer?'#,##0':'0.0000'):'@');
 });
 sh.getRangeByIndexes(0,0,1,m).format=head;sh.tables.add(sh.getRangeByIndexes(0,0,n,m),true,'Stability'+name);sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(name==='RepeatedOOF'?3:2);sh.showGridLines=false;
 if(name==='Cases'){const note=sh.getRangeByIndexes(1,m+1,1,1);note.values=[[d.source_note]];note.format={font:{name:'Arial',size:10,color:'#536474'},columnWidth:210};}
}
for(const [name,data]of Object.entries(d.datasets))table(name,data);
const ref=(name,key,row)=>`'${name}'!${letter(d.datasets[name].headers.indexOf(key)+1)}${row}`;
const span=(name,key)=>`${ref(name,key,2)}:${letter(d.datasets[name].headers.indexOf(key)+1)}${d.datasets[name].rows.length+1}`;
function block(name,groupKey,groupValue,key){
 const data=d.datasets[name],j=data.headers.indexOf(groupKey),ix=data.rows.map((r,i)=>r[j]===groupValue?i+2:null).filter(x=>x!==null);
 if(ix.at(-1)-ix[0]+1!==ix.length)throw new Error('Expected contiguous summary block');
 return `${ref(name,key,ix[0])}:${letter(data.headers.indexOf(key)+1)}${ix.at(-1)}`;
}
const sh=sheets.Summary;sh.showGridLines=false;sh.tabColor='#35556D';
sh.getRange('B2').values=[['固定模型的稳定性与单扫描敏感性']];sh.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
sh.getRange('B4:H4').values=[['20套固定重复','AUC中位数','最低AUC','最高AUC','Brier中位数','治疗改变识别率中位数','完整重复数']];
const models=['M0','M1','MRI','Fusion'],labels=['年龄＋性别','扩展临床','MRI八项','临床＋MRI'];
for(let i=0;i<4;i++){
 sh.getRange(`B${i+5}`).values=[[labels[i]]];
 const range=k=>block('RepeatMetrics','model',models[i],k);
 sh.getRange(`C${i+5}:H${i+5}`).formulas=[[`=MEDIAN(${range('roc_auc')})`,`=MIN(${range('roc_auc')})`,`=MAX(${range('roc_auc')})`,`=MEDIAN(${range('brier')})`,`=MEDIAN(${range('specificity_treatment_change')})`,`=COUNT(${range('roc_auc')})`]];
}
sh.getRange('B12:I12').values=[['每患者单扫描','OOF AUC','95%下限','95%上限','Brier','治疗改变识别数','肿瘤识别数','平衡准确率']];
for(let i=0;i<4;i++){
 const r=d.datasets.SingleMetrics.rows.findIndex(x=>x[0]===models[i])+2;sh.getRange(`B${i+13}`).values=[[labels[i]]];
 sh.getRange(`C${i+13}:I${i+13}`).formulas=[['roc_auc','roc_auc_ci_lower','roc_auc_ci_upper','brier','tn','tp','balanced_accuracy'].map(k=>'='+ref('SingleMetrics',k,r))];
}
sh.getRange('B19:F19').values=[['重复Fusion减临床','差值中位数','最低差值','最高差值','有利方向套数']];
for(const [row,key,label,sign]of [[20,'roc_auc','AUC差','>0'],[21,'brier','Brier差（负值较好）','<0']]){
 const range=block('RepeatDeltas','metric',key,'difference');sh.getRange(`B${row}`).values=[[label]];
 sh.getRange(`C${row}:F${row}`).formulas=[[`=MEDIAN(${range})`,`=MIN(${range})`,`=MAX(${range})`,`=COUNTIFS(${range},"${sign}")`]];
}
sh.getRange('B24:E24').values=[['单扫描Fusion减临床','差值','95%下限','95%上限']];
for(const [row,key,label]of [[25,'roc_auc','AUC差'],[26,'brier','Brier差']]){
 const ci=d.summary.single_scan.bootstrap_95ci['Fusion_minus_M1__'+key];sh.getRange(`B${row}:E${row}`).values=[[label,null,ci.lower,ci.upper]];
 const fusion=d.datasets.SingleMetrics.rows.findIndex(x=>x[0]==='Fusion')+2,clinical=d.datasets.SingleMetrics.rows.findIndex(x=>x[0]==='M1')+2;
 sh.getRange(`C${row}`).formulas=[[`=${ref('SingleMetrics',key,fusion)}-${ref('SingleMetrics',key,clinical)}`]];
}
sh.getRange('B29:C29').values=[['扫描选择与完整性','数量']];sh.getRange('B30:B34').values=[['全部有影像扫描'],['选中单扫描'],['单扫描肿瘤'],['单扫描治疗改变'],['成功重复']];
sh.getRange('C30:C34').formulas=[
 [`=COUNTA(${span('Cases','ID')})`],[`=COUNTIFS(${span('Cases','selected')},1)`],
 [`=COUNTIFS(${span('Cases','selected')},1,${span('Cases','tumor_label')},1)`],
 [`=COUNTIFS(${span('Cases','selected')},1,${span('Cases','tumor_label')},0)`],
 [`=COUNTIFS(${span('RepeatStatus','complete')},1)`]];
sh.getRange('E29').values=[['解释']];sh.getRange('E30:E34').values=[
 ['重复范围是分折描述，不是95%置信区间。'],['同一批患者反复使用，20套并非独立研究。'],
 ['单扫描按最小可用会话编号，不称首次就诊。'],['单扫描与182条主分析不能直接作增量比较。'],['95%区间仅用于单扫描患者配对bootstrap。']];
sh.getRange('B37:B39').values=[['保持第18步原主分析，不选择最高重复或改变阈值。'],['单扫描仅22次治疗改变，增量区间跨零，证据仍不确定。'],['Excel数据改动不重新训练Python模型；后续工作等待批准。']];
sh.getRange('B4:I39').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:29,verticalAlignment:'center'};
sh.getRange('B4:B39').format.columnWidth=34;sh.getRange('C4:F39').format.columnWidth=19;sh.getRange('G4:I39').format.columnWidth=27;
for(const r of ['B4:H4','B12:I12','B19:F19','B24:E24','B29:C29','E29'])sh.getRange(r).format=head;
sh.getRange('C5:F8').setNumberFormat('0.000');sh.getRange('G5:G8').setNumberFormat('0.0%');sh.getRange('H5:H8').setNumberFormat('0');
sh.getRange('C13:F16').setNumberFormat('0.000');sh.getRange('G13:H16').setNumberFormat('0');sh.getRange('I13:I16').setNumberFormat('0.0%');
sh.getRange('C20:E21').setNumberFormat('0.0000');sh.getRange('F20:F21').setNumberFormat('0');sh.getRange('C25:E26').setNumberFormat('0.0000');sh.getRange('C30:C34').setNumberFormat('0');
wb.recalculate();
if(sh.getRange('C31').values[0][0]!==135||sh.getRange('C33').values[0][0]!==22||sh.getRange('C34').values[0][0]!==20)throw new Error('Selection counts do not reconcile');
const flag=sheets.Cases.getRange(ref('Cases','selected',2).split('!')[1]),original=flag.values[0][0];if(original!==1)throw new Error('Unexpected first selection flag');
flag.values=[[0]];wb.recalculate();if(sh.getRange('C31').values[0][0]!==134||sh.getRange('C33').values[0][0]!==21)throw new Error('Selection formula did not update');flag.values=[[original]];wb.recalculate();
await fs.mkdir(outputDir,{recursive:true});await fs.writeFile(path.join(outputDir,'summary.inspect.ndjson'),(await wb.inspect({kind:'table',range:'Summary!B4:I26',include:'values,formulas',tableMaxRows:23,tableMaxCols:8,maxChars:6000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:1200})).ndjson);
for(const [name,range]of [['Summary','B2:I39'],['RepeatMetrics','A1:J7'],['RepeatDeltas','A1:E7'],['SingleMetrics','A1:J5'],['Cases','A1:F7'],['SingleOOF','A1:J6'],['RepeatedOOF','A1:J6'],['RepeatStatus','A1:D8']]){
 const blob=await wb.render({sheetName:name,range,scale:1.1,format:'png'});await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_Model_Stability.xlsx'));
console.log(JSON.stringify({exported:true,sheets:names,selection_count_recalculation_verified:true,temporary_edit_restored:true}));
