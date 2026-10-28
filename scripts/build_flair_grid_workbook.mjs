import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;
if(!root)throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/flair-grid-qc-20261028');
const data=JSON.parse(await fs.readFile(path.join(root,'reports/flair_grid_workbook_input.json'),'utf8'));
const wb=Workbook.create(),summary=wb.worksheets.add('Summary');
const letter=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
const span=(name,key)=>{const t=data.sheets.find(t=>t.name===name),c=letter(t.headers.indexOf(key)+1);return `${name}!${c}2:${c}${t.rows.length+1}`;};
for(const t of data.sheets){
 const s=wb.worksheets.add(t.name),n=t.rows.length+1,m=t.headers.length;
 s.showGridLines=false;s.getRangeByIndexes(0,0,n,m).values=[t.headers,...t.rows];
 s.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:26,verticalAlignment:'center'};
 for(let j=0;j<m;j++){
  const key=t.headers[j],r=s.getRangeByIndexes(0,j,n,1),text=t.rows.some(row=>typeof row[j]==='string');
  r.format.columnWidth=/member|sha256/.test(key)?76:/name|status|comparison/.test(key)?50:Math.max(19,Math.min(38,key.length*.9));
  r.setNumberFormat(text?'@':/fraction/.test(key)?'0.00%':/difference_mm/.test(key)?'0.000000000':/mm|EchoTime|InversionTime|Thickness/.test(key)?'0.000000':'#,##0');
  s.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment=text?'left':'right';
 }
 s.getRangeByIndexes(0,0,1,m).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:56,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
 s.tables.add(`A1:${letter(m)}${n}`,true,`${t.name}FlairGridTable`);
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(t.name==='Files'?2:1);
 if(t.name==='Files'){
  s.getRange(`C2:C${n}`).format.wrapText=true;s.getRangeByIndexes(1,0,n-1,m).format.rowHeight=48;
 }
 if(t.name==='Pairs'){
  s.getRange(`D2:D${n}`).conditionalFormats.add('cellIs',{operator:'equal',formula:0,format:{fill:'#FFF1D6',font:{color:'#844F00',bold:true}}});
  s.getRange(`F2:F${n}`).conditionalFormats.addCustom('AND(ISNUMBER(F2),F2<1)',{fill:'#FFF1D6',font:{color:'#844F00',bold:true}});
 }
}
summary.showGridLines=false;summary.tabColor='#244969';
summary.getRange('B2').values=[['FLAIR配对与坐标差异复核']];summary.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
summary.getRange('B4:D4').values=[['指标','结果','单位']];
const metrics=[
 ['基线病灶候选',`=COUNTA(${span('Pairs','lesion_key')})`,'个'],
 ['有FLAIR名称候选的病灶',`=SUM(${span('Pairs','flair_candidate_found')})`,'个'],
 ['未找到FLAIR名称候选',`=COUNTIFS(${span('Pairs','flair_candidate_found')},0)`,'个'],
 ['FLAIR序列',`=COUNTA(${span('FLAIRSeries','series_name')})`,'组'],
 ['FLAIR切片',`=SUM(${span('FLAIRSeries','files')})`,'张'],
 ['像素可读取',`=SUM(${span('Files','pixel_decodable')})`,'张'],
 ['几何检查通过序列',`=SUM(${span('FLAIRSeries','technical_stack_pass')})`,'组'],
 ['有采集层间隙序列',`=SUM(${span('FLAIRSeries','interslice_gap_present')})`,'组'],
 ['坐标视野完整包含目标',`=COUNTIFS(${span('Pairs','coordinate_fov_fraction')},1)`,'个'],
 ['坐标视野部分包含目标',`=COUNTIFS(${span('Pairs','coordinate_fov_fraction')},"<1",${span('Pairs','flair_candidate_found')},1)`,'个'],
 ['待复核坐标差异病灶',`=COUNTA(${span('GridReview','lesion_key')})`,'个'],
 ['其中qform敏感性满足容差',`=SUM(${span('GridReview','qform_grid_equivalent')})`,'个'],
 ['已解决坐标差异',`=SUM(${span('GridReview','review_resolved')})`,'个']
];
summary.getRange(`B5:D${4+metrics.length}`).values=metrics.map(r=>[r[0],null,r[2]]);
metrics.forEach((r,i)=>summary.getRange(`C${i+5}`).formulas=[[r[1]]]);
summary.getRange('F4').values=[['解释']];
summary.getRange('F5:F12').values=[['48组基线检查中40组有FLAIR名称候选。'],['46个病灶可作后续配对审阅候选。'],['40158_L1的坐标视野覆盖98.30%。'],['共有148个目标体素中心超出FLAIR坐标范围。'],['相同空间UID不等于解剖配准成功。'],['20034_L1、L2仅在qform敏感性检查中达标。'],['当前统一使用sform，42/12原判定不变。'],['尚未配准、修改标签或训练预测模型。']];
summary.getRange('B20').values=[['坐标视野覆盖不代表运动校正、采集层间隙覆盖或临床图像质量通过。']];
summary.getRange('B22').values=[['日期为去标识编码。qform与sform的差异原因仍需来源证据核实。']];
summary.getRange('B4:F22').format.font={name:'Arial',size:11,color:'#263747'};
summary.getRange('B4:D17').format.rowHeight=30;
summary.getRange('B4:D4').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center'};
summary.getRange('B4:B22').format.columnWidth=38;summary.getRange('C4:C22').format.columnWidth=15;
summary.getRange('D4:D22').format.columnWidth=9;summary.getRange('E4:E22').format.columnWidth=4;summary.getRange('F4:F22').format.columnWidth=73;
summary.getRange('C5:C17').setNumberFormat('#,##0');summary.getRange('C5:C17').format.horizontalAlignment='right';
const source=wb.worksheets.getItem('Files');
source.getRange('L1:M4').values=[['来源','说明'],['https://molab.es/datasets-brain-metastasis-1/','原始公开数据库；逐文件成员与SHA见明细'],['https://nipy.org/nibabel/nifti_images.html','NiBabel对sform、qform的选择'],['https://nifti.nimh.nih.gov/nifti-1/documentation/faq/index.html','NIfTI格式及两种空间变换']];
source.getRange('L1:M4').format={font:{name:'Arial',size:10},rowHeight:26,verticalAlignment:'center'};
source.getRange('L1:L4').format.columnWidth=105;source.getRange('M1:M4').format.columnWidth=66;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:D17',include:'values,formulas',tableMaxRows:15,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const name of ['Summary','Pairs','GridReview','FLAIRSeries','Files']){
 const p=await wb.render({sheetName:name,range:name==='Summary'?'B2:F23':'A1:H6',scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);await file.save(path.join(outputDir,'RN_FLAIR_Grid_Review.xlsx'));
console.log('Exported RN_FLAIR_Grid_Review.xlsx');
