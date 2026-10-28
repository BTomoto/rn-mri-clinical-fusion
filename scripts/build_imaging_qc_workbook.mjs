import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const root=process.env.RN_PROJECT_ROOT;
if(!root)throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/imaging-qc-20261028');
const data=JSON.parse(await fs.readFile(path.join(root,'reports/imaging_qc_workbook_input.json'),'utf8'));
const wb=Workbook.create(),summary=wb.worksheets.add('Summary');
const letter=n=>{let x='';while(n){n--;x=String.fromCharCode(65+n%26)+x;n=Math.floor(n/26);}return x;};
const span=(name,key)=>{const t=data.sheets.find(s=>s.name===name);return `${name}!${letter(t.headers.indexOf(key)+1)}2:${letter(t.headers.indexOf(key)+1)}${t.rows.length+1}`;};
for(const t of data.sheets){
 const s=wb.worksheets.add(t.name),n=t.rows.length+1,m=t.headers.length;
 s.showGridLines=false;
 s.getRangeByIndexes(0,0,n,m).values=[t.headers,...t.rows];
 s.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:25,verticalAlignment:'center'};
 for(let j=0;j<m;j++){
  const key=t.headers[j],r=s.getRangeByIndexes(0,j,n,1),text=t.rows.some(row=>typeof row[j]==='string');
  r.format.columnWidth=/member|sha256/.test(key)?74:/status|reason|Description/.test(key)?48:Math.max(18,Math.min(30,key.length*.75));
  r.setNumberFormat(text?'@':/mm|error_voxels|Spacing|Thickness/.test(key)?'0.000000':'#,##0');
  s.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment=text?'left':'right';
 }
 s.getRangeByIndexes(0,0,1,m).format={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:48,horizontalAlignment:'center',verticalAlignment:'center'};
 s.tables.add(`A1:${letter(m)}${n}`,true,`${t.name}QCTable`);
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(t.name==='Files'?2:1);
 if(t.name==='Series')s.getRange(`H2:H${n}`).conditionalFormats.add('cellIs',{operator:'equal',formula:1,format:{fill:'#FFF1D6',font:{color:'#844F00',bold:true}}});
}
const files=wb.worksheets.getItem('Files');
files.getRange('R1:S6').values=[['来源','说明'],['https://molab.es/datasets-brain-metastasis-1/','原始数据库及下载入口'],['https://figshare.com/articles/dataset/22271017','DICOMs_2.zip：本轮1,254个成员'],['https://figshare.com/articles/dataset/22271233','DICOMs_4.zip：本轮330个成员'],['https://dicom.nema.org/medical/dicom/2026c/output/chtml/part03/sect_C.7.6.2.html','DICOM空间坐标方法'],['https://nipy.org/nibabel/coordinate_systems.html','LPS转RAS及NIfTI坐标']];
files.getRange('R1:S6').format={font:{name:'Arial',size:10},rowHeight:25,verticalAlignment:'center'};
files.getRange('R1:R6').format.columnWidth=105;files.getRange('S1:S6').format.columnWidth=48;
summary.showGridLines=false;summary.tabColor='#244969';
summary.getRange('B2').values=[['新增基线MRI技术质控']];
summary.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
summary.getRange('B4:D4').values=[['指标','结果','单位']];
const metrics=[
 ['检查',4,'组'],
 ['DICOM切片',`=SUM(${span('Series','files')})`,'张'],
 ['像素可读取',`=SUM(${span('Files','pixel_decodable')})`,'张'],
 ['SHA256匹配',`=SUM(${span('Files','sha256_match')})`,'张'],
 ['CRC32匹配',`=SUM(${span('Files','crc32_match')})`,'张'],
 ['技术检查通过序列',`=SUM(${span('Series','technical_stack_pass')})`,'组'],
 ['层间距标签不一致',`=SUM(${span('Series','spacing_tag_position_mismatch')})`,'组'],
 ['T2-FLAIR名称候选',`=SUM(${span('Series','t2_flair_metadata_candidate')})`,'组'],
 ['T1-FLAIR另列',`=SUM(${span('Series','t1_flair_name')})`,'组'],
 ['投影或重建序列',`=SUM(${span('Series','derived_or_projection_hint')})`,'组'],
 ['新增检查中有基线匹配的病灶',`=COUNTA(${span('Lesions','lesion_key')})`,'个'],
 ['有同期分割',`=SUM(${span('Lesions','baseline_mask_available')})`,'个'],
 ['分割网格等价',`=SUM(${span('Lesions','grid_equivalent')})`,'个']
];
summary.getRange(`B5:D${4+metrics.length}`).values=metrics.map(r=>[r[0],typeof r[1]==='number'?r[1]:null,r[2]]);
metrics.forEach((r,i)=>{if(typeof r[1]==='string')summary.getRange(`C${i+5}`).formulas=[[r[1]]];});
summary.getRange('F4').values=[['结果解释']];
summary.getRange('F5:F12').values=[['范围为4组新增基线检查。'],['28个序列均可构成规则单帧影像堆栈。'],['3个层间距标签与实际坐标不一致。'],['T2-FLAIR候选均存在采集层间隙。'],['40093_L3的397个分割体素全部在图像内。'],['分割对齐为两轴翻转，无插值。'],['其余6个病灶候选无同期公开分割。'],['对比剂给药时间仍未核实。']];
summary.getRange('B20').values=[['全队列影像质控、跨序列配准与临床结局核实仍待完成。']];
summary.getRange('B22').values=[['日期为原始数据的去标识时间编码。技术检查通过不等于临床质量通过。']];
summary.getRange('B4:F22').format.font={name:'Arial',size:11,color:'#263747'};
summary.getRange('B4:D17').format.rowHeight=29;
summary.getRange('B4:D4').format={fill:'#244969',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center'};
summary.getRange('B4:B22').format.columnWidth=38;
summary.getRange('C4:C22').format.columnWidth=15;
summary.getRange('D4:D22').format.columnWidth=10;
summary.getRange('E4:E22').format.columnWidth=4;
summary.getRange('F4:F22').format.columnWidth=67;
summary.getRange('C5:C17').setNumberFormat('#,##0');
summary.getRange('C5:C17').format.horizontalAlignment='right';
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:D17',include:'values,formulas',tableMaxRows:15,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const name of ['Summary',...data.sheets.map(s=>s.name)]){
 const p=await wb.render({sheetName:name,range:name==='Summary'?'B2:F23':name==='Files'?'A1:H5':'A1:H6',scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await p.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(path.join(outputDir,'RN_Additional_Imaging_QC.xlsx'));
console.log('Exported RN_Additional_Imaging_QC.xlsx');
