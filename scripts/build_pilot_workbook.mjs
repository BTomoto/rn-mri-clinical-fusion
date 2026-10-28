import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/registration-pilot-20261029');
const data=JSON.parse(await fs.readFile(path.join(root,'reports/pilot_workbook_input.json'),'utf8'));
const wb=Workbook.create(),s=wb.worksheets.add('Summary'),trials=wb.worksheets.add('Trials'),sources=wb.worksheets.add('Sources');
const letter=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
trials.getRangeByIndexes(0,0,data.rows.length+1,data.headers.length).values=[data.headers,...data.rows];
trials.getRangeByIndexes(0,0,data.rows.length+1,data.headers.length).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:28,verticalAlignment:'center'};
data.headers.forEach((key,j)=>{
 const r=trials.getRangeByIndexes(0,j,data.rows.length+1,1),text=data.rows.some(row=>typeof row[j]==='string');
 r.format.columnWidth=/attempt|status/.test(key)?55:Math.max(20,Math.min(38,key.length*.9));
 r.setNumberFormat(text?'@':/overlap|fov/.test(key)?'0.00%':/mi_|mm|degrees/.test(key)?'0.000000':'#,##0');
 trials.getRangeByIndexes(1,j,data.rows.length,1).format.horizontalAlignment=text?'left':'right';
});
trials.getRange(`A1:${letter(data.headers.length)}1`).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:60,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
trials.tables.add(`A1:${letter(data.headers.length)}7`,true,'PilotTrialsTable');trials.freezePanes.freezeRows(1);trials.freezePanes.freezeColumns(2);
trials.getRange('F2:F7').conditionalFormats.add('cellIs',{operator:'equal',formula:0,format:{fill:'#FFF1D6',font:{color:'#844F00',bold:true}}});
const g=data.gate;
sources.getRange('A1:B7').values=[['原定模型所需数据','已核实数量或标记'],['临床病灶',g.clinical_lesions],['数值型RN时间',g.recorded_rn_times],['RN结局未知',g.unknown_rn],['已核实阴性',g.verified_non_events],['已核实事件无发生截止',g.verified_event_free_followup_records],['原风险模型条件具备',g.original_risk_prediction_model_ready?1:0]];
sources.getRange('D1:F6').values=[['核查日期','公开来源','判断依据'],...data.sources];
sources.getRange('A1:F7').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:36,verticalAlignment:'center'};
sources.getRange('A1:A7').format.columnWidth=34;sources.getRange('B1:B7').format.columnWidth=25;sources.getRange('C1:C7').format.columnWidth=4;
sources.getRange('D1:D7').format.columnWidth=17;sources.getRange('E1:E7').format.columnWidth=90;sources.getRange('F1:F7').format.columnWidth=70;
sources.getRange('E2:F6').format.wrapText=true;sources.getRange('D2:F6').format.rowHeight=54;sources.getRange('B2:B7').setNumberFormat('#,##0');
for(const r of ['A1:B1','D1:F1'])sources.getRange(r).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:42,horizontalAlignment:'center'};
s.getRange('B2').values=[['配准试验与建模条件核查']];s.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
s.getRange('B4:G4').values=[['步长受控重试','负互信息：之前','负互信息：候选之后','变化值','工程筛查','后续状态']];
for(let i=0;i<3;i++){
 const row=i+5,sourceRow=i+5;
 s.getRange(`B${row}`).formulas=[[`=Trials!B${sourceRow}`]];
 s.getRange(`C${row}:G${row}`).formulas=[[
  `=Trials!C${sourceRow}`,`=Trials!D${sourceRow}`,`=D${row}-C${row}`,`=Trials!F${sourceRow}`,`=IF(F${row}=1,"仅供解剖复核","拒绝候选变换")`
 ]];
}
s.getRange('B10').values=[['负互信息越低越好；变化值为正表示变差。候选变换均未用于分析。']];
s.getRange('B12:D12').values=[['结局条件','已核实数量','解释']];
const info=[['数值型RN时间',3,'仅表示原表有时间记录'],['RN结局未知',4,'空白不编码为阴性'],['已核实阴性',5,'仍缺少可追溯阴性结局'],['事件无发生截止',6,'MRI日期不等于无事件截止']];
info.forEach((r,i)=>{let row=13+i;s.getRange(`B${row}`).values=[[r[0]]];s.getRange(`C${row}`).formulas=[[`=Sources!B${r[1]}`]];s.getRange(`D${row}`).values=[[r[2]]];});
s.getRange('B19').values=[['决定：暂不扩大全队列自动配准；原定风险模型不训练。']];
s.getRange('B21').values=[['优先解决公开终点依据或完整公开标签队列；3例试验不代表全队列质量。']];
s.getRange('B4:G21').format.font={name:'Arial',size:11,color:'#263747'};
s.getRange('B4:G7').format.rowHeight=35;s.getRange('B4:G4').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:48,wrapText:true,horizontalAlignment:'center'};
s.getRange('B4:B21').format.columnWidth=32;s.getRange('C4:F21').format.columnWidth=24;s.getRange('G4:G21').format.columnWidth=30;
s.getRange('C5:E7').setNumberFormat('0.0000');s.getRange('F5:F7').setNumberFormat('0');s.getRange('C5:F7').format.horizontalAlignment='right';
s.getRange('B12:D12').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:35};s.getRange('B13:D16').format.rowHeight=32;
s.getRange('D13:F16').format.columnWidth=32;s.getRange('C13:C16').setNumberFormat('#,##0');
s.tabColor='#244969';for(const sheet of [s,trials,sources])sheet.showGridLines=false;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:G7',include:'values,formulas',tableMaxRows:5,tableMaxCols:6})).ndjson);
console.log((await wb.inspect({kind:'table',range:'Summary!B12:D16',include:'values,formulas',tableMaxRows:5,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const name of ['Summary','Trials','Sources']){
 const p=await wb.render({sheetName:name,range:name==='Summary'?'B2:G22':name==='Sources'?'A1:F7':'A1:H7',scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);await file.save(path.join(outputDir,'RN_Registration_Pilot_and_Model_Gate.xlsx'));console.log('Exported pilot workbook');
