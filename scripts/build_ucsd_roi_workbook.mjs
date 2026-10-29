import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const outputDir=path.join(root,'outputs/ucsd-roi-pilot-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_roi_workbook_input.json'),'utf8'));
const wb=Workbook.create(),sheets=Object.fromEntries(['Summary','ROI','Processing','Files','Histograms'].map(n=>[n,wb.worksheets.add(n)]));
const letter=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
const head={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:48};
function reorder(data,first){const h=[...first,...data.headers.filter(x=>!first.includes(x))];return {headers:h,rows:data.rows.map(r=>h.map(k=>r[data.headers.indexOf(k)]))};}
const datasets={ROI:reorder(d.cases,['ID','tumor_label','roi_voxels','erosion_voxels','erosion_retention','components_26','success']),Processing:reorder(d.processing,['ID','sequence','p01','p99','clipped_high_fraction','normalized_minimum','normalized_maximum','occupied_bins','erosion_JS_distance','success']),Files:reorder(d.files,['ID','sequence','bytes','decoded','digest_matches','relative_grid_status','physical_QC_pass','spatial_units']),Histograms:d.histograms};
function table(name,data){
 const sh=sheets[name],n=data.rows.length+1,m=data.headers.length;
 sh.getRangeByIndexes(0,0,n,m).values=[data.headers,...data.rows.map(row=>row.map(v=>typeof v==='boolean'?Number(v):v))];
 sh.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:29,verticalAlignment:'center'};
 data.headers.forEach((key,j)=>{
  const col=sh.getRangeByIndexes(0,j,n,1);
  col.format.columnWidth=/sha256/.test(key)?70:/url/.test(key)?155:/path|mask$|label_source/.test(key)?76:/^ID$|patient_id|brats_ID/.test(key)?30:/error|issues|rule/.test(key)?50:Math.max(16,Math.min(29,key.length*.85));
  const numeric=data.rows.some(r=>typeof r[j]==='number');
  col.setNumberFormat(numeric?(/fraction|retention/.test(key)?'0.0%':/minimum|maximum|mean|std|JS|probability/.test(key)?'0.0000':'#,##0'):'@');
 });
 sh.getRangeByIndexes(0,0,1,m).format=head;
 sh.tables.add(sh.getRangeByIndexes(0,0,n,m),true,'Pilot'+name);
 sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(2);sh.showGridLines=false;
}
for(const [name,data]of Object.entries(datasets))table(name,data);
const span=(tab,key)=>`${tab}!${letter(datasets[tab].headers.indexOf(key)+1)}2:${letter(datasets[tab].headers.indexOf(key)+1)}${datasets[tab].rows.length+1}`;
const sh=sheets.Summary;sh.showGridLines=false;sh.tabColor='#35556D';
sh.getRange('B2').values=[['六例MRI：ROI与强度处理试验']];sh.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
sh.getRange('B4:C4').values=[['实际完成','数量']];
const rows=[['源患者/扫描',`=COUNTA(${span('ROI','ID')})`],['源影像文件',`=COUNTA(${span('Files','ID')})`],['源文件字节',`=SUM(${span('Files','bytes')})`],['完整体素解码',`=COUNTIF(${span('Files','decoded')},1)`],['相对原生网格一致',`=COUNTIF(${span('Files','relative_grid_status')},"native_matrix_match")`],['物理尺度质控通过',`=COUNTIF(${span('Files','physical_QC_pass')},1)`],['统一ROI成功',`=COUNTIF(${span('ROI','success')},1)`],['不裁切处理成功',`=COUNTIF(${span('Processing','success')},1)`]];
sh.getRange('B5:C12').values=rows.map(r=>[r[0],null]);rows.forEach((r,i)=>sh.getRange(`C${i+5}`).formulas=[[r[1]]]);
sh.getRange('B15:D15').values=[['技术诊断范围','下限','上限']];
sh.getRange('B16:D19').values=[['一次腐蚀体素保留',null,null],['不裁切边界JS距离',null,null],['原方案上端裁切比例',null,null],['不裁切派生强度范围',null,null]];
for(const [r,tab,key]of [[16,'ROI','erosion_retention'],[17,'Processing','erosion_JS_distance'],[18,'Processing','clipped_high_fraction']])sh.getRange(`C${r}:D${r}`).formulas=[[`=MIN(${span(tab,key)})`,`=MAX(${span(tab,key)})`]];
sh.getRange('C19:D19').formulas=[[`=MIN(${span('Processing','normalized_minimum')})`,`=MAX(${span('Processing','normalized_maximum')})`]];
sh.getRange('E4:E11').values=[['本步范围'],['6名不同患者；两类各3例，仅为技术样本。'],['标记1=是、0=否；体素数量不代表mL体积。'],['所有空间单位unknown，未自动补成mm。'],['30份源强度图均为uint8；ADC不作定量输入。'],['普通分割全部正标签并集，不称纯肿瘤。'],['未训练MRI模型，也未估计AUC。'],['Excel记录源文件、处理参数和两套箱计数。']];
sh.getRange('E15:E22').values=[['后续固定处理建议'],['每图p1/p99线性缩放，不裁切尾部。'],['允许小于0或大于1，不作为错误值删除。'],['原ROI固定32箱，边界诊断沿用相同箱边界。'],['修正在观察裁切损失后追加，并非预注册。'],['不使用类别、AUC或显著性选择方法。'],['下一阶段：批量有限特征提取，等待批准。'],['用户无需下载或准备文件。']];
sh.getRange('B4:E22').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:32,verticalAlignment:'center'};
sh.getRange('B4:B22').format.columnWidth=32;sh.getRange('C4:D22').format.columnWidth=20;sh.getRange('E4:E22').format.columnWidth=76;
for(const r of ['B4:C4','B15:D15','E4','E15'])sh.getRange(r).format=head;
sh.getRange('C5:C12').setNumberFormat('#,##0');sh.getRange('C16:D16').setNumberFormat('0.0%');sh.getRange('C18:D18').setNumberFormat('0.0%');sh.getRange('C17:D17').setNumberFormat('0.000');sh.getRange('C19:D19').setNumberFormat('0.000');
wb.recalculate();
if(sh.getRange('C7').values[0][0]!==43455955||sh.getRange('C12').values[0][0]!==24||sh.getRange('C10').values[0][0]!==0)throw new Error('Pilot counts mismatch');
const successCol=letter(datasets.Processing.headers.indexOf('success')+1),cell=sheets.Processing.getRange(`${successCol}2`);cell.values=[[0]];wb.recalculate();if(sh.getRange('C12').values[0][0]!==23)throw new Error('Dynamic success count failed');cell.values=[[1]];wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:D19',include:'values,formulas',tableMaxRows:16,tableMaxCols:3,maxChars:2000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const [name,range]of [['Summary','B2:E22'],['ROI','A1:G7'],['Processing','A1:J6'],['Files','A1:H6'],['Histograms','A1:H6']]){
 const p=await wb.render({sheetName:name,range,scale:1.15,format:'png'});await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_ROI_Intensity_Pilot.xlsx'));
console.log('Exported ROI/intensity pilot workbook');
