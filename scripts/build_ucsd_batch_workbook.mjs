import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const outputDir=path.join(root,'outputs/ucsd-batch-features-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_batch_workbook_input.json'),'utf8'));
const names=['Summary','Features','Sensitivity','Cases','Files','Definitions','Diagnostics'];
const wb=Workbook.create(),sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const letter=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
const head={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:48};
const datasets=Object.fromEntries(names.filter(n=>n!=='Summary').map(n=>[n,d.datasets[n]]));
function table(name,data){
 const sh=sheets[name],n=data.rows.length+1,m=data.headers.length;
 sh.getRangeByIndexes(0,0,n,m).values=[data.headers,...data.rows.map(r=>r.map(v=>typeof v==='boolean'?Number(v):v))];
 sh.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:27,verticalAlignment:'center'};
 data.headers.forEach((key,j)=>{
  const col=sh.getRangeByIndexes(0,j,n,1);const vals=data.rows.map(r=>r[j]);
  col.format.columnWidth=/sha256/.test(key)?70:/^url$/.test(key)?155:/label_source|diagnosis_raw|normalization|sensitivity|definition|native_affine/.test(key)?90:/ID$|patient_id|validation_group/.test(key)?30:/status|error|ROI/.test(key)?46:Math.max(18,Math.min(30,key.length*.85));
  const numeric=vals.some(v=>typeof v==='number'||typeof v==='boolean');
  col.setNumberFormat(numeric?(/retention|fraction/.test(key)?'0.0%':/mean|std|entropy|contrast|minimum|maximum|bin_min|bin_max|p01|p99|log_initial/.test(key)?'0.0000':'#,##0'):'@');
 });
 sh.getRangeByIndexes(0,0,1,m).format=head;
 sh.tables.add(sh.getRangeByIndexes(0,0,n,m),true,'Batch'+name);sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(2);sh.showGridLines=false;
 // Sources beside the flat import table, outside the data/table range.
 const notes=sh.getRangeByIndexes(1,m+1,1,1);notes.values=[[d.source_note]];notes.format={font:{name:'Arial',size:10,color:'#536474'},columnWidth:210,rowHeight:27};
}
for(const [name,data]of Object.entries(datasets))table(name,data);
const span=(tab,key)=>`'${tab}'!${letter(datasets[tab].headers.indexOf(key)+1)}2:${letter(datasets[tab].headers.indexOf(key)+1)}${datasets[tab].rows.length+1}`;
const sh=sheets.Summary;sh.showGridLines=false;sh.tabColor='#35556D';
sh.getRange('B2').values=[['批量MRI特征与临床连接']];sh.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
sh.getRange('B4:C4').values=[['本阶段实际结果','扫描或文件数']];
const items=[
 ['原临床队列',`=COUNTA(${span('Cases','ID')})`],
 ['影像特征完整扫描',`=COUNTA(${span('Features','ID')})`],
 ['肿瘤扫描',`=COUNTIFS(${span('Features','tumor_label')},1)`],
 ['治疗改变扫描',`=COUNTIFS(${span('Features','tumor_label')},0)`],
 ['镜像目录未覆盖扫描',`=COUNTIFS(${span('Cases','status')},"not_listed_in_current_mirror")`],
 ['提取失败扫描',`=COUNTIFS(${span('Cases','status')},"processing_failed")`],
 ['实际文件完整解码',`=COUNTIFS(${span('Files','decoded')},1)`],
 ['源文件SHA256一致',`=COUNTIFS(${span('Files','digest_matches')},1)`],
 ['空间单位unknown文件',`=COUNTIFS(${span('Files','spatial_units')},"unknown")`],
 ['腐蚀特征完整扫描',`=COUNTIFS(${span('Cases','eroded_complete')},1)`],
 ['源文件字节',`=SUM(${span('Files','bytes')})`]
];
sh.getRange('B5:C15').values=items.map(r=>[r[0],null]);items.forEach((r,i)=>sh.getRange(`C${i+5}`).formulas=[[r[1]]]);
sh.getRange('E4').values=[['使用范围与限制']];
sh.getRange('E5:E13').values=[
 [`${d.summary.primary_source_patients}名源患者；多次扫描不作为独立患者。`],
 ['FLAIR与增强T1，每个序列4项固定特征。'],
 ['源标注全部正标签并集；标注盲法未确认。'],
 ['每图p1/p99线性缩放，不裁切尾部。'],
 ['unknown空间单位不补成mm；不计算体积。'],
 ['uint8派生图像；不能恢复原始定量强度。'],
 ['腐蚀仅用于边界敏感性，不按结果挑选特征。'],
 ['本阶段未训练MRI模型或计算AUC。'],
 ['下一阶段：共同病例分组建模，等待用户批准。']];
sh.getRange('B18:D18').values=[['技术诊断','最小值','最大值']];
sh.getRange('B19:D20').values=[['一次腐蚀体素保留比例',null,null],['ROI归一化后强度范围',null,null]];
sh.getRange('C19:D19').formulas=[[`=MIN(${span('Cases','erosion_retention')})`,`=MAX(${span('Cases','erosion_retention')})`]];
sh.getRange('C20:D20').formulas=[[`=MIN(${span('Diagnostics','normalized_minimum')})`,`=MAX(${span('Diagnostics','normalized_maximum')})`]];
sh.getRange('B4:E20').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:31,verticalAlignment:'center'};
sh.getRange('B4:B20').format.columnWidth=35;sh.getRange('C4:D20').format.columnWidth=21;sh.getRange('E4:E20').format.columnWidth=78;
for(const range of ['B4:C4','E4','B18:D18'])sh.getRange(range).format=head;
sh.getRange('C5:C15').setNumberFormat('#,##0');sh.getRange('C19:D19').setNumberFormat('0.0%');sh.getRange('C20:D20').setNumberFormat('0.000');
wb.recalculate();
if(sh.getRange('C6').values[0][0]!==d.summary.primary_complete_timepoints||sh.getRange('C10').values[0][0]!==d.summary.target_failed_timepoints||sh.getRange('C11').values[0][0]!==d.summary.files_decoded)throw new Error('Summary counts do not reconcile');
// Verify live summary logic, then restore the temporary source edit.
const flag=sheets.Files.getRange(`${letter(datasets.Files.headers.indexOf('decoded')+1)}2`),old=flag.values[0][0];flag.values=[[0]];wb.recalculate();
if(sh.getRange('C10').values[0][0]!==d.summary.target_failed_timepoints||sh.getRange('C11').values[0][0]!==d.summary.files_decoded-1)throw new Error('Dynamic decode count failed');
flag.values=[[old]];wb.recalculate();
await fs.mkdir(outputDir,{recursive:true});
const inspection=await wb.inspect({kind:'table',range:'Summary!B4:D20',include:'values,formulas',tableMaxRows:17,tableMaxCols:3,maxChars:4500});
await fs.writeFile(path.join(outputDir,'summary.inspect.ndjson'),inspection.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:1200});console.log(errors.ndjson);
for(const [name,range]of [['Summary','B2:E20'],['Features','A1:L6'],['Sensitivity','A1:I6'],['Cases','A1:G6'],['Files','A1:H6'],['Definitions','A1:D5'],['Diagnostics','A1:H6']]){
 const p=await wb.render({sheetName:name,range,scale:1.1,format:'png'});await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_Clinical_Image_Features.xlsx'));
console.log(JSON.stringify({exported:true,worksheets:names,decoded_count_recalculation_verified:true,temporary_edits_restored:true}));
