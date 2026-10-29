import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const outputDir=path.join(root,'outputs/ucsd-mri-mirror-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_mirror_workbook_input.json'),'utf8'));
const wb=Workbook.create();
const summary=wb.worksheets.add('Summary'),files=wb.worksheets.add('Files'),coverage=wb.worksheets.add('Coverage');
const head={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:44};
function table(sh,data,name){
 const n=data.rows.length+1,m=data.headers.length;
 sh.getRangeByIndexes(0,0,n,m).values=[data.headers,...data.rows.map(row=>row.map(v=>typeof v==='boolean'?Number(v):v))];
 sh.getRangeByIndexes(0,0,n,m).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:29,verticalAlignment:'center',columnWidth:22};
 sh.getRangeByIndexes(0,0,1,m).format=head;
 sh.tables.add(sh.getRangeByIndexes(0,0,n,m),true,name);
 sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(2);
}
table(files,d.files,'ActualMirrorFiles');table(coverage,d.coverage,'ClinicalMirrorCoverage');
files.getRange('A1:A13').format.columnWidth=31;files.getRange('B1:B13').format.columnWidth=19;
files.getRange('C1:E13').format.columnWidth=17;files.getRange('F1:I13').format.columnWidth=20;
files.getRange('J1:J13').format.columnWidth=29;files.getRange('K1:L13').format.columnWidth=13;
files.getRange('M1:M13').format.columnWidth=33;files.getRange('N1:N13').format.columnWidth=26;
files.getRange('O1:O13').format.columnWidth=71;files.getRange('P1:P13').format.columnWidth=160;files.getRange('Q1:Q13').format.columnWidth=79;
files.getRange('C2:C13').setNumberFormat('#,##0');files.getRange('K2:L13').setNumberFormat('0.000');
files.getRange('G2:G13').conditionalFormats.add('containsText',{text:'unknown',format:{fill:'#FFF3CF',font:{color:'#7A4900'}}});
files.getRange('I2:I13').conditionalFormats.add('cellIs',{operator:'equal',formula:0,format:{fill:'#FBE6E5',font:{color:'#9F2424'}}});
coverage.getRange('A1:C239').format.columnWidth=31;coverage.getRange('D1:D239').format.columnWidth=14;
coverage.getRange('E1:E239').format.columnWidth=69;coverage.getRange('F1:N239').format.columnWidth=23;
summary.getRange('B2').values=[['两例MRI镜像下载与技术检查']];summary.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
summary.getRange('B4:D4').values=[['实际样本','数值','说明']];
const counts=[
 ['已取得扫描', '=COUNTIF(Coverage!N2:N239,1)','0002_01与0005_01，仅作技术试验'],
 ['实际影像文件','=COUNTA(Files!A2:A13)','每例5份强度图及1份普通分割'],
 ['影像字节','=SUM(Files!C2:C13)','按12份实际下载文件计'],
 ['完整体素解码','=COUNTIF(Files!D2:D13,1)','标记1=是、0=否；完整3D读取'],
 ['镜像SHA256一致','=COUNTIF(Files!E2:E13,1)','与镜像声明校验值一致'],
 ['原生相对网格一致','=COUNTIF(Files!J2:J13,"native_matrix_match")','没有为unknown单位赋予毫米尺度'],
 ['完整物理质控通过','=COUNTIF(Files!I2:I13,1)','空间单位缺失，保留未通过状态'],
 ['空间单位unknown','=COUNTIF(Files!G2:G13,"unknown")','不能直接计算mm或mL体积'],
 ];
summary.getRange('B5:D12').values=counts.map(r=>[r[0],null,r[2]]);counts.forEach((r,i)=>summary.getRange(`C${i+5}`).formulas=[[r[1]]]);
summary.getRange('B15:D15').values=[['目录覆盖候选（未全部下载）','数值','说明']];
summary.getRange('B16:D20').values=[['六序列齐全扫描',null,'现有临床238条中可对应的目录'],['其中肿瘤扫描',null,'沿用源标签，不从分割推断'],['其中治疗改变扫描',null,'包括多种治疗相关改变'],['六序列不齐或未列出',null,'仍保留在临床队列'],['六序列候选源患者',d.summary.listed_all_six_remaining_patients,'Python按源患者ID去重']];
summary.getRange('C16:C19').formulas=[['=COUNTIF(Coverage!L2:L239,1)'],['=COUNTIFS(Coverage!L2:L239,1,Coverage!D2:D239,1)'],['=COUNTIFS(Coverage!L2:L239,1,Coverage!D2:D239,0)'],['=COUNTA(Coverage!A2:A239)-C16']];
summary.getRange('B23:D23').values=[['实际观测限制','状态','后续意义']];
summary.getRange('B24:D27').values=[['10份强度图像','uint8 / 0–255','ADC不能解释成原始物理ADC'],['预测ROI','尚未建立','普通分割目前仅作技术叠加'],['MRI预测模型','未拟合','两例不估计诊断性能'],['下一步','待批准','扩展少量病例，固定统一ROI及强度处理方案']];
summary.getRange('B4:D27').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:32,verticalAlignment:'center'};
summary.getRange('B4:B27').format.columnWidth=34;summary.getRange('C4:C27').format.columnWidth=23;summary.getRange('D4:D27').format.columnWidth=69;
for(const range of ['B4:D4','B15:D15','B23:D23'])summary.getRange(range).format=head;
summary.getRange('C5:C20').setNumberFormat('#,##0');
for(const sh of [summary,files,coverage])sh.showGridLines=false;summary.tabColor='#35556D';
wb.recalculate();
if(summary.getRange('C7').values[0][0]!==14251565||summary.getRange('C16').values[0][0]!==182||summary.getRange('C11').values[0][0]!==0)throw new Error('Counts not reconciled');
const cell=files.getRange('D2'),before=summary.getRange('C8').values[0][0];cell.values=[[0]];wb.recalculate();
if(summary.getRange('C8').values[0][0]!==before-1)throw new Error('Decoded count does not react to input');cell.values=[[1]];wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B4:D20',include:'values,formulas',tableMaxRows:17,tableMaxCols:3,maxChars:2500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const [name,range] of [['Summary','B2:D27'],['Files','A1:J6'],['Coverage','A1:D9']]){
 const b=await wb.render({sheetName:name,range,scale:1.2,format:'png'});await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await b.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_MRI_Mirror_Samples.xlsx'));
console.log('Exported actual MRI sample workbook');
