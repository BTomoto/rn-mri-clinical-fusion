import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const outputDir=path.join(root,'outputs/ucsd-fusion-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_fusion_workbook_input.json'),'utf8'));
const names=['Summary','Metrics','Comparisons','OOF','Inputs','Eroded','Folds','Calibration','Coefficients'];
const wb=Workbook.create(),sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const letter=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
const head={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:46};
function table(name,data){
 const sh=sheets[name],n=data.rows.length+1,m=data.headers.length;
 sh.getRangeByIndexes(0,0,n,m).values=[data.headers,...data.rows.map(r=>r.map(v=>typeof v==='boolean'?Number(v):v))];
 sh.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:27,verticalAlignment:'center'};
 data.headers.forEach((key,j)=>{
  const col=sh.getRangeByIndexes(0,j,n,1),vals=data.rows.map(r=>r[j]);
  col.format.columnWidth=/label_source|primary_diagnosis_raw|fit$/.test(key)?85:/comparison/.test(key)?44:/ID$|patient_id|validation_group|term$/.test(key)?35:Math.max(17,Math.min(29,key.length*.85));
  const numeric=vals.some(v=>typeof v==='number'||typeof v==='boolean');
  const integer=/^(fold|validation_fold|n_train|n_test|n_test_patients|test_tumor|test_treatment_change|bin|n|tn|fp|fn|tp|tumor_count|tumor_label|sex_male|other_treatment_prior|initial_event_missing|age_years|days_since_initial_event)$/.test(key)||/prediction_0_5$/.test(key);
  col.setNumberFormat(numeric?(integer?'#,##0':'0.0000'):'@');
 });
 sh.getRangeByIndexes(0,0,1,m).format=head;sh.tables.add(sh.getRangeByIndexes(0,0,n,m),true,'Fusion'+name);sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(name==='Inputs'||name==='OOF'?2:1);sh.showGridLines=false;
 if(['Inputs','Eroded'].includes(name)){
  const note=sh.getRangeByIndexes(1,m+1,1,1);note.values=[[d.source_note]];note.format={font:{name:'Arial',size:10,color:'#536474'},columnWidth:210};
 }
}
for(const [name,data]of Object.entries(d.datasets))table(name,data);
const reference=(name,key,row)=>`'${name}'!${letter(d.datasets[name].headers.indexOf(key)+1)}${row}`;
const span=(name,key)=>`${reference(name,key,2)}:${letter(d.datasets[name].headers.indexOf(key)+1)}${d.datasets[name].rows.length+1}`;
const sh=sheets.Summary;sh.showGridLines=false;sh.tabColor='#35556D';
sh.getRange('B2').values=[['临床、MRI与融合模型比较']];sh.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
sh.getRange('B4:I4').values=[['模型','OOF AUC','95%下限','95%上限','Brier','治疗改变识别数','肿瘤识别数','平衡准确率']];
const modelNames=['M0','M1','MRI','Fusion','MRI_eroded','Fusion_eroded'];
const labels=['年龄＋性别','扩展临床','MRI八项','临床＋MRI','腐蚀MRI','腐蚀临床＋MRI'];
for(let i=0;i<modelNames.length;i++){
 const dataRow=d.datasets.Metrics.rows.findIndex(r=>r[0]===modelNames[i])+2;
 sh.getRange(`B${i+5}`).values=[[labels[i]]];
 sh.getRange(`C${i+5}:I${i+5}`).formulas=[['roc_auc','roc_auc_ci_lower','roc_auc_ci_upper','brier','tn','tp','balanced_accuracy'].map(key=>'='+reference('Metrics',key,dataRow))];
}
sh.getRange('B13:E13').values=[['融合减临床','差值','95%下限','95%上限']];
for(const [i,metric,label]of [[14,'roc_auc','AUC差（主要比较）'],[15,'brier','Brier差（负值较好）'],[16,'ap_treatment_change','治疗改变AP差']]){
 const h=d.datasets.Comparisons.headers;const row=d.datasets.Comparisons.rows.findIndex(r=>r[h.indexOf('comparison')]==='Fusion_minus_M1'&&r[h.indexOf('metric')]===metric)+2;
 sh.getRange(`B${i}`).values=[[label]];sh.getRange(`C${i}:E${i}`).formulas=[['difference','lower','upper'].map(key=>'='+reference('Comparisons',key,row))];
}
sh.getRange('B19:C19').values=[['共同病例','扫描数']];sh.getRange('B20:B23').values=[['总扫描'],['肿瘤扫描'],['治疗改变扫描'],['间隔缺失扫描']];
sh.getRange('C20:C23').formulas=[[`=COUNTA(${span('Inputs','ID')})`],[`=COUNTIFS(${span('Inputs','tumor_label')},1)`],[`=COUNTIFS(${span('Inputs','tumor_label')},0)`],[`=SUM(${span('Inputs','initial_event_missing')})`]];
sh.getRange('E19').values=[['结果解释']];sh.getRange('E20:E23').values=[
 ['135名患者，同一患者及BraTS患者不跨折。'],
 ['固定0.5阈值；治疗改变分母41，肿瘤分母141。'],
 ['患者bootstrap固定OOF概率，未重拟合模型。'],
 ['全队列系数仅描述，性能全部来自OOF预测。']];
sh.getRange('B26:B29').values=[['固定C=1、L2正则，无调参、特征筛选或阈值优化。'],['腐蚀版本仅作敏感性，原ROI仍是主分析。'],['8位派生强度，空间单位unknown，标注盲法未确认。'],['没有外部验证；下一阶段等待用户批准。']];
sh.getRange('B4:I29').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:30,verticalAlignment:'center'};
sh.getRange('B4:B29').format.columnWidth=32;sh.getRange('C4:F29').format.columnWidth=18;sh.getRange('G4:I29').format.columnWidth=24;
for(const r of ['B4:I4','B13:E13','B19:C19','E19'])sh.getRange(r).format=head;
sh.getRange('C5:F10').setNumberFormat('0.000');sh.getRange('G5:H10').setNumberFormat('0');sh.getRange('I5:I10').setNumberFormat('0.0%');sh.getRange('C14:E16').setNumberFormat('0.0000');sh.getRange('C20:C23').setNumberFormat('0');
wb.recalculate();
if(sh.getRange('C20').values[0][0]!==182||sh.getRange('C22').values[0][0]!==41)throw new Error('Cohort count mismatch');
const primary=d.summary.metrics.Fusion.roc_auc;if(Math.abs(sh.getRange('C8').values[0][0]-primary)>1e-12)throw new Error('Fusion AUC mismatch');
const input=sheets.Metrics.getRange(reference('Metrics','roc_auc',5).split('!')[1]);const original=input.values[0][0];input.values=[[.123]];wb.recalculate();
if(sh.getRange('C8').values[0][0]!==.123)throw new Error('Summary does not update');input.values=[[original]];wb.recalculate();
await fs.mkdir(outputDir,{recursive:true});
await fs.writeFile(path.join(outputDir,'summary.inspect.ndjson'),(await wb.inspect({kind:'table',range:'Summary!B4:I16',include:'values,formulas',tableMaxRows:13,tableMaxCols:8,maxChars:6000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:1200})).ndjson);
for(const [name,range]of [['Summary','B2:I29'],['Metrics','A1:L8'],['Comparisons','A1:F8'],['OOF','A1:J6'],['Inputs','A1:J6'],['Eroded','A1:I6'],['Folds','A1:L7'],['Calibration','A1:F7'],['Coefficients','A1:D7']]){
 const blob=await wb.render({sheetName:name,range,scale:1.1,format:'png'});await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_Clinical_MRI_Fusion.xlsx'));
console.log(JSON.stringify({exported:true,sheets:names,summary_recalculation_verified:true,temporary_edit_restored:true}));
