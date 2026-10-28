import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/public-label-audit-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/label_audit_workbook_input.json'),'utf8'));
const wb=Workbook.create(),s=wb.worksheets.add('Summary'),t=wb.worksheets.add('Timepoints'),src=wb.worksheets.add('Sources');
const letter=n=>{let x='';while(n){n--;x=String.fromCharCode(65+n%26)+x;n=Math.floor(n/26);}return x;};
const span=key=>{let c=letter(d.headers.indexOf(key)+1);return `Timepoints!${c}2:${c}${d.rows.length+1}`;};
const n=d.rows.length+1,m=d.headers.length;
t.getRangeByIndexes(0,0,n,m).values=[d.headers,...d.rows];
t.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:27,verticalAlignment:'center'};
d.headers.forEach((key,j)=>{
 const r=t.getRangeByIndexes(0,j,n,1),text=d.rows.some(row=>typeof row[j]==='string');
 r.format.columnWidth=/source$|status|Diagnosis/.test(key)?68:Math.max(23,Math.min(38,key.length*.9));
 r.setNumberFormat(text?'@':'#,##0');t.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment=text?'left':'right';
});
t.getRangeByIndexes(0,0,1,m).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:58,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
t.tables.add(`A1:${letter(m)}${n}`,true,'LabelAuditTimepoints');t.freezePanes.freezeRows(1);t.freezePanes.freezeColumns(2);
src.getRange('A1:B5').values=[['官网/论文亚型介绍','时间点数'],...d.counts.map(r=>[r.subtype,r.published_description_count])];
src.getRange('A8:B11').values=[['原脑转移瘤队列','记录数'],['数值型RN时间',35],['结局未知',125],['已核实阴性',0]];
src.getRange('D1:F5').values=[['来源','URL','核查结果'],...d.sources];
src.getRange('A1:F11').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:30,verticalAlignment:'center'};
src.getRange('A1:A11').format.columnWidth=39;src.getRange('B1:B11').format.columnWidth=23;src.getRange('C1:C11').format.columnWidth=4;
src.getRange('D1:D11').format.columnWidth=24;src.getRange('E1:E11').format.columnWidth=100;src.getRange('F1:F11').format.columnWidth=73;
src.getRange('D2:F5').format.wrapText=true;src.getRange('D2:F5').format.rowHeight=64;
for(const r of ['A1:B1','A8:B8','D1:F1'])src.getRange(r).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:38,wrapText:true,horizontalAlignment:'center'};
s.getRange('B2').values=[['公开标签核查：本步未建模']];s.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
s.getRange('B4:D4').values=[['新候选队列资料','本轮核查','单位']];
const metrics=[
 ['检查时间点',`=COUNTA(${span('ID')})`,'次'],['患者（去重）',d.summary.ucsd_patients,'名'],
 ['肿瘤候选时间点',`=SUM(${span('broad_tumor_label_candidate')})`,'次'],
 ['治疗相关改变时间点',`=COUNTIFS(${span('broad_tumor_label_candidate')},0)`,'次'],
 ['明确RN记录时间点',`=COUNTIFS(${span('negative_list_dx')},"Radiation necrosis")`,'次'],
 ['明确RN患者（去重）',d.summary.explicit_rn_patients,'名'],['当前启用建模',`=SUM(${span('use_for_model')})`,'条']
];
s.getRange('B5:D11').values=metrics.map(r=>[r[0],typeof r[1]==='number'?r[1]:null,r[2]]);
metrics.forEach((r,i)=>{if(typeof r[1]==='string')s.getRange(`C${i+5}`).formulas=[[r[1]]];});
s.getRange('F4').values=[['本步结论']];
s.getRange('F5:F11').values=[['原脑转移瘤RN风险预测标签仍未补足。'],['RN-D3附录已核查，未提供逐病灶标签表。'],['新文件仅4名明确RN患者，不建议单独建RN模型。'],['243=192肿瘤候选+51治疗相关改变。'],['这是高级别胶质瘤鉴别问题，需批准改题。'],['11名患者跨两类时间点，验证须按患者分组。'],['未下载新队列MRI，未训练新模型。']];
s.getRange('B14:D14').values=[['亚型计数核对','官网/论文介绍','下载文件实际']];
d.counts.forEach((r,i)=>{
 const row=i+15;s.getRange(`B${row}`).values=[[r.subtype]];
 s.getRange(`C${row}`).formulas=[[`=Sources!B${i+2}`]];
 s.getRange(`D${row}`).formulas=[[`=COUNTIFS(${span('negative_list_dx')},"${r.subtype}")`]];
});
s.getRange('B19').values=[['合计']];s.getRange('C19:D19').formulas=[['=SUM(C15:C18)','=SUM(D15:D18)']];
s.getRange('F15:F18').values=[['保留文件原值，未按介绍补造RN病例。'],['192个肿瘤候选标签按作者总分组推导。'],['不是逐例病理重新判定，也不是RN阴性标签。'],['原研究题目及所有建模启用标记均未改变。']];
s.getRange('B22').values=[['待批准计划：改为肿瘤与治疗相关改变的探索性鉴别，先核对患者分组，再跑基础临床Logistic模型。']];
s.getRange('B24').values=[['本步到此结束，等待用户批准后再进入下一步。']];
s.getRange('B4:F24').format.font={name:'Arial',size:11,color:'#263747'};
s.getRange('B4:D19').format.rowHeight=31;s.getRange('B4:B24').format.columnWidth=36;s.getRange('C4:D24').format.columnWidth=22;
s.getRange('E4:E24').format.columnWidth=4;s.getRange('F4:F24').format.columnWidth=80;
for(const r of ['B4:D4','B14:D14'])s.getRange(r).format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:42,wrapText:true,horizontalAlignment:'center'};
s.getRange('B15:B18').format.wrapText=true;s.getRange('B15:D18').format.rowHeight=42;
s.getRange('C5:D19').setNumberFormat('#,##0');
s.tabColor='#244969';for(const sh of [s,t,src])sh.showGridLines=false;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:D11',include:'values,formulas',tableMaxRows:9,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'table',range:'Summary!B14:D19',include:'values,formulas',tableMaxRows:7,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const name of ['Summary','Timepoints','Sources']){
 const p=await wb.render({sheetName:name,range:name==='Summary'?'B2:F25':name==='Sources'?'A1:F11':'A1:H6',scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
const out=await SpreadsheetFile.exportXlsx(wb);await out.save(path.join(outputDir,'RN_Public_Label_Feasibility.xlsx'));console.log('Exported public-label audit workbook');
