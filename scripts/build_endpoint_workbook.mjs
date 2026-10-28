import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const root=process.env.RN_PROJECT_ROOT;
if(!root)throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/endpoint-followup-20261028');
const data=JSON.parse(await fs.readFile(path.join(root,'reports/endpoint_workbook_input.json'),'utf8'));
const old=JSON.parse(await fs.readFile(path.join(root,'reports/readiness_audit.json'),'utf8'));
await fs.mkdir(outputDir,{recursive:true});
const wb=Workbook.create(),overview=wb.worksheets.add('Summary');
const letter=n=>{let x='';while(n){n--;x=String.fromCharCode(65+n%26)+x;n=Math.floor(n/26);}return x;};
const spec=name=>data.sheets.find(x=>x.name===name);
const span=(name,key)=>{const s=spec(name),c=letter(s.headers.indexOf(key)+1);return `${name}!${c}2:${c}${s.rows.length+1}`;};
for(const t of data.sheets){
 const s=wb.worksheets.add(t.name),n=t.rows.length+1,m=t.headers.length;
 s.showGridLines=false;
 s.getRangeByIndexes(0,0,n,m).values=[t.headers,...t.rows];
 s.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:24,verticalAlignment:'center'};
 for(let j=0;j<m;j++){
  const key=t.headers[j],r=s.getRangeByIndexes(0,j,n,1),isText=t.rows.some(row=>typeof row[j]==='string');
  r.format.columnWidth=/finding|interpretation|action|license_note|use$/.test(key)?85:
   /sha256|url|file|Image|Mask/.test(key)?64:/status|class|version|scope/.test(key)?42:Math.max(17,Math.min(36,key.length*.8));
  r.setNumberFormat(isText?'@':/shape_|firstorder_|volume/.test(key)?'0.0000':'0');
  s.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment=isText?'left':'right';
  if(t.rows.some(row=>typeof row[j]==='string'&&row[j].length>85)){
   s.getRangeByIndexes(1,j,n-1,1).format.wrapText=true;
   s.getRangeByIndexes(1,0,n-1,m).format.rowHeight=64;
  }
 }
 s.getRangeByIndexes(0,0,1,m).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:54,horizontalAlignment:'center',verticalAlignment:'center'};
 s.tables.add(`A1:${letter(m)}${n}`,true,`${t.name}Table`);
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(1);
 if(t.name==='Sources')s.getRange(`A2:${letter(m)}${n}`).format.rowHeight=100;
}
overview.showGridLines=false;overview.tabColor='#244969';
overview.getRange('B2').values=[['临床版本更新与随访资料核查']];
overview.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
overview.getRange('B4:F4').values=[['指标','Figshare旧版','作者网站当前版',null,'解释']];
const metrics=[
 ['患者',old.outcomes.patients,data.summary.patients,'两版患者编号可一一对应'],
 ['病灶记录',old.outcomes.clinical_lesions,`=COUNTA(${span('ClinicalCurrent','lesion_key')})`,'160个病灶编号可一一对应'],
 ['有数值型坏死时间',old.outcomes.recorded_rn_times,`=COUNT(${span('ClinicalCurrent','rn_time_day')})`,'新增3条，另修改3条既有时间'],
 ['坏死状态未知',old.outcomes.unknown_rn,`=COUNTIFS(${span('ClinicalCurrent','rn_status')},"unknown")`,'空白不编码为阴性'],
 ['首次SRS时间有记录',107,`=COUNT(${span('ClinicalCurrent','first_srs_start_day')})`,'补充8条首次SRS起始时间'],
 ['基线影像目录候选',old.outcomes.baseline_directory_candidates,`=SUM(${span('Followup','baseline_directory_candidate')})`,'SRS前30天，且严格早于治疗'],
 ['有实际基线掩膜的病灶',old.outcomes.baseline_actual_mask_lesions,`=SUM(${span('Followup','baseline_mask_available')})`,'仍需定位与完整影像质控'],
 ['基线掩膜候选患者',old.outcomes.baseline_actual_mask_patients,data.summary.baseline_mask_patients,'患者内病灶相关性须保留'],
 ['其中有记录的坏死时间',old.outcomes.baseline_actual_mask_rn_times,`=COUNT(${span('BaselineFeatures','rn_time_day')})`,'其余36个候选仍为未知'],
 ['已确认阴性对照',0,`=SUM(${span('ClinicalCurrent','verified_non_event')})`,'当前未建立可追溯的阴性结局']
];
overview.getRange('B5:F14').values=metrics.map(r=>[r[0],r[1],typeof r[2]==='number'?r[2]:null,null,r[3]]);
metrics.forEach((r,i)=>{if(typeof r[2]==='string')overview.getRange(`D${i+5}`).formulas=[[r[2]]];});
overview.getRange('B17:G17').values=[['核查人群','期限（天）','病灶记录','MRI达期限','掩膜达期限','期限内记录坏死时间']];
const h=key=>span('Horizon',key),rows=[];
for(const [label,base] of [['有可用SRS索引',null],['基线掩膜候选',1]]){
 for(const horizon of [180,365]){
  const criteria=`${h('horizon_days')},${horizon}`+(base===null?'':`,${h('baseline_mask_candidate')},1`);
  const sr=18+rows.length;
  rows.push([label,horizon,null,null,null,null]);
  overview.getRange(`D${sr}:G${sr}`).formulas=[[
   `=COUNTIFS(${criteria})`,
   `=SUMIFS(${h('source_scan_on_or_after_horizon_before_death')},${criteria})`,
   `=SUMIFS(${h('lesion_mask_on_or_after_horizon_before_death')},${criteria})`,
   `=SUMIFS(${h('recorded_rn_time_within_horizon')},${criteria})`
  ]];
 }
}
// Write labels without overwriting the formula cells.
overview.getRange('B18:C21').values=rows.map(r=>r.slice(0,2));
overview.getRange('B23').values=[['MRI达期限只表示检查资料存在，不能证明此前未发生坏死。各列可重叠，不能相加。']];
overview.getRange('B25:D25').values=[['当前判断','结局证据仍不足','暂不拟合风险预测模型']];
overview.getRange('B27').values=[['180日和365日仅用于资料覆盖核查，尚未选定正式预测期限。相对日期以去标识时间轴为准。']];
overview.getRange('B29').values=[['当前版来自原作者公开下载按钮；旧版保留。影像组学特征仍明确引用已核验的Figshare版本。']];
overview.getRange('B4:G29').format.font={name:'Arial',size:11,color:'#263747'};
overview.getRange('B4:D4').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32};
overview.getRange('F4').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'}};
overview.getRange('B17:G17').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:42,wrapText:true,horizontalAlignment:'center'};
overview.getRange('B5:G29').format.rowHeight=32;
overview.getRange('B2:B29').format.columnWidth=32;
overview.getRange('C2:D29').format.columnWidth=23;
overview.getRange('E2:E16').format.columnWidth=22;
overview.getRange('F2:G29').format.columnWidth=34;
overview.getRange('C5:D14').format.horizontalAlignment='center';
overview.getRange('C5:D14').setNumberFormat('#,##0');
overview.getRange('C18:G21').format.horizontalAlignment='center';
overview.getRange('C18:G21').setNumberFormat('#,##0');
// Explanation spans two otherwise unused columns in the opening table.
overview.getRange('F5:G14').format.wrapText=true;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:F14',include:'values,formulas',tableMaxRows:12,tableMaxCols:5})).ndjson);
console.log((await wb.inspect({kind:'table',range:'Summary!B17:G21',include:'values,formulas',tableMaxRows:5,tableMaxCols:6})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20}})).ndjson);
for(const name of ['Summary',...data.sheets.map(s=>s.name)]){
 const range=name==='Summary'?'B2:G30':name==='Sources'?'A1:E3':'A1:H5';
 const p=await wb.render({sheetName:name,range,scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(path.join(outputDir,'RN_Endpoint_Followup.xlsx'));
console.log('Exported RN_Endpoint_Followup.xlsx');
