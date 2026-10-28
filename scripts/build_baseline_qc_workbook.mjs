import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;
if(!root)throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/baseline-qc-20261028');
const data=JSON.parse(await fs.readFile(path.join(root,'reports/baseline_qc_workbook_input.json'),'utf8'));
const wb=Workbook.create(),summary=wb.worksheets.add('Summary');
const letter=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
const span=(name,key)=>{const t=data.sheets.find(t=>t.name===name),c=letter(t.headers.indexOf(key)+1);return `${name}!${c}2:${c}${t.rows.length+1}`;};
for(const t of data.sheets){
 const s=wb.worksheets.add(t.name),n=t.rows.length+1,m=t.headers.length;
 s.showGridLines=false;
 s.getRangeByIndexes(0,0,n,m).values=[t.headers,...t.rows];
 s.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:25,verticalAlignment:'center'};
 for(let j=0;j<m;j++){
  const key=t.headers[j],r=s.getRangeByIndexes(0,j,n,1),text=t.rows.some(row=>typeof row[j]==='string');
  r.format.columnWidth=/member|sha256/.test(key)?76:/name|status|estimator/.test(key)?52:Math.max(19,Math.min(38,key.length*.9));
  r.setNumberFormat(text?'@':/mm|error_voxels|Spacing/.test(key)?'0.000000':'#,##0');
  s.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment=text?'left':'right';
 }
 s.getRangeByIndexes(0,0,1,m).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:52,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
 s.tables.add(`A1:${letter(m)}${n}`,true,`${t.name}BaselineQCTable`);
 if(t.name==='Files'){
  s.getRange(`C2:C${n}`).format.wrapText=true;
  s.getRangeByIndexes(1,0,n-1,m).format.rowHeight=48;
 }else{
  for(let i=0;i<t.rows.length;i++)if(t.rows[i].some(v=>typeof v==='string'&&v.length>65)){
   s.getRangeByIndexes(i+1,0,1,m).format.rowHeight=50;
   s.getRangeByIndexes(i+1,0,1,m).format.wrapText=true;
  }
 }
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(t.name==='Files'?2:1);
 if(t.name==='Lesions')s.getRange(`D2:D${n}`).conditionalFormats.add('cellIs',{operator:'equal',formula:0,format:{fill:'#FFF1D6',font:{color:'#844F00',bold:true}}});
 if(t.name==='Series')s.getRange(`I2:I${n}`).conditionalFormats.add('cellIs',{operator:'equal',formula:1,format:{fill:'#FFF1D6',font:{color:'#844F00',bold:true}}});
}
summary.showGridLines=false;summary.tabColor='#244969';
summary.getRange('B2').values=[['基线分割对应MRI全序列质控']];
summary.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
summary.getRange('B4:D4').values=[['指标','结果','单位']];
const metrics=[
 ['患者',41,'名'],['检查',48,'组'],
 ['切片',`=SUM(${span('Series','files')})`,'张'],
 ['像素可读取',`=SUM(${span('Files','pixel_decodable')})`,'张'],
 ['SHA256匹配',`=SUM(${span('Files','sha256_match')})`,'张'],
 ['序列几何检查通过',`=SUM(${span('Series','technical_stack_pass')})`,'组'],
 ['病灶候选',`=COUNTA(${span('Lesions','lesion_key')})`,'个'],
 ['掩膜网格匹配',`=SUM(${span('Lesions','grid_equivalent')})`,'个'],
 ['网格误差待复核',`=COUNTIFS(${span('Lesions','grid_equivalent')},0)`,'个'],
 ['层间距标签不一致',`=SUM(${span('Series','spacing_tag_position_mismatch')})`,'组'],
 ['常量切片',`=SUM(${span('Files','constant_pixel_array')})`,'张'],
 ['目标体素位于常量切片',`=SUM(${span('Lesions','target_voxels_on_constant_slices')})`,'个'],
 ['投影或重建序列',`=SUM(${span('Series','derived_or_projection_hint')})`,'组']
];
summary.getRange(`B5:D${4+metrics.length}`).values=metrics.map(r=>[r[0],typeof r[1]==='number'?r[1]:null,r[2]]);
metrics.forEach((r,i)=>{if(typeof r[1]==='string')summary.getRange(`C${i+5}`).formulas=[[r[1]]];});
summary.getRange('F4').values=[['解释']];
summary.getRange('F5:F12').values=[['覆盖54个病灶的掩膜对应序列。'],['仅本次选定序列，不代表全部MRI或FLAIR。'],['42个符合0.001体素网格容差。'],['12个超阈值，保留原数据并列待复核。'],['最大角点差异约0.104毫米。'],['标点名称变体均保留可追溯对应。'],['常量切片未涉及目标体素。'],['配准、临床图像质量与结局仍待核实。']];
summary.getRange('B20').values=[['工程容差不代表临床可接受阈值；网格匹配不是RN诊断。']];
summary.getRange('B22').values=[['日期为去标识编码。未插值、重画标签或拟合预测模型。']];
summary.getRange('B4:F22').format.font={name:'Arial',size:11,color:'#263747'};
summary.getRange('B4:D17').format.rowHeight=29;
summary.getRange('B4:D4').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center'};
summary.getRange('B4:B22').format.columnWidth=35;summary.getRange('C4:C22').format.columnWidth=16;
summary.getRange('D4:D22').format.columnWidth=9;summary.getRange('E4:E22').format.columnWidth=4;
summary.getRange('F4:F22').format.columnWidth=66;
summary.getRange('C5:C17').setNumberFormat('#,##0');summary.getRange('C5:C17').format.horizontalAlignment='right';
const files=wb.worksheets.getItem('Files');
files.getRange('L1:M4').values=[['来源','说明'],['https://molab.es/datasets-brain-metastasis-1/','公开原始数据库'],['https://nipy.org/nibabel/dicom/dicom_orientation.html','首末切片构造多切片仿射'],['https://dicom.nema.org/medical/dicom/2026c/output/chtml/part03/sect_C.7.6.2.html','图像平面空间坐标；具体原始成员及SHA见明细']];
files.getRange('L1:M4').format={font:{name:'Arial',size:10},rowHeight:25,verticalAlignment:'center'};
files.getRange('L1:L4').format.columnWidth=105;files.getRange('M1:M4').format.columnWidth=65;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:D17',include:'values,formulas',tableMaxRows:15,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const name of ['Summary','Lesions','Series','Files']){
 const p=await wb.render({sheetName:name,range:name==='Summary'?'B2:F23':'A1:H6',scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);await file.save(path.join(outputDir,'RN_Baseline_Mask_Series_QC.xlsx'));
console.log('Exported RN_Baseline_Mask_Series_QC.xlsx');
