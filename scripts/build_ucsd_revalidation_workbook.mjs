import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT required');
const outputDir=path.join(root,'outputs/ucsd-clinical-revalidation-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_revalidation_workbook_input.json'),'utf8'));
const s=d.summary,m=s.metrics,ci=s.patient_cluster_bootstrap_95ci;
const wb=Workbook.create(),sheets=Object.fromEntries(['Summary','OOF','Folds','Sensitivity','Scope'].map(n=>[n,wb.worksheets.add(n)]));
const letter=n=>{let x='';while(n){n--;x=String.fromCharCode(65+n%26)+x;n=Math.floor(n/26);}return x;};
const head={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:58,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
function table(sh,obj,startRow=1,name='Data'){
 const n=obj.rows.length+1,cols=obj.headers.length;
 sh.getRangeByIndexes(startRow-1,0,n,cols).values=[obj.headers,...obj.rows];
 sh.getRangeByIndexes(startRow-1,0,n,cols).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:28,verticalAlignment:'center'};
 obj.headers.forEach((key,j)=>{
  const isText=obj.rows.some(r=>typeof r[j]==='string');const range=sh.getRangeByIndexes(startRow-1,j,n,1);
  range.format.columnWidth=/source|reason|meaning|Diagnosis|diagnosis/.test(key)?64:Math.max(22,Math.min(35,key.length*.86));
  range.setNumberFormat(isText?'@':/probability|error|brier|auc|accuracy|sensitivity|specificity|ap_/.test(key)?'0.000000':'#,##0');
  sh.getRangeByIndexes(startRow,j,n-1,1).format.horizontalAlignment=isText?'left':'right';
 });
 sh.getRangeByIndexes(startRow-1,0,1,cols).format=head;
 sh.tables.add(`A${startRow}:${letter(cols)}${startRow+n-1}`,true,name);
 return sh;
}
const oofHeaders=[...d.oof.headers,...['M0_squared_error','M1_squared_error','prior_squared_error']];
table(sheets.OOF,{headers:oofHeaders,rows:d.oof.rows.map(r=>[...r,null,null,null])},1,'ClinicalRevalidationOOF');
const ocol=k=>letter(oofHeaders.indexOf(k)+1),ospan=k=>`OOF!${ocol(k)}2:${ocol(k)}239`;
for(let row=2;row<=239;row++)for(const model of ['M0','M1','prior']){
 sheets.OOF.getRange(`${ocol(model+'_prediction_0_5')}${row}`).formulas=[[`=IF(${ocol(model+'_oof_probability')}${row}>=Scope!$B$9,1,0)`]];
 sheets.OOF.getRange(`${ocol(model+'_squared_error')}${row}`).formulas=[[`=(${ocol('tumor_label')}${row}-${ocol(model+'_oof_probability')}${row})^2`]];
}
sheets.OOF.freezePanes.freezeRows(1);sheets.OOF.freezePanes.freezeColumns(2);
table(sheets.Folds,d.fold_metrics,1,'ClinicalRevalidationFolds');sheets.Folds.freezePanes.freezeRows(1);
table(sheets.Folds,d.preprocessing,15,'ClinicalFoldPreprocessing');sheets.Folds.getRange('B16:E20').setNumberFormat('0.000000');
const coef=[];for(const name of ['M0','M1']){
 const p=s.final_full_cohort_parameters[name];coef.push([name,'intercept',p.intercept,'全队列描述/重建，不是独立危险因素推断']);
 p.feature_order.forEach((feature,i)=>coef.push([name,feature,p.coefficients[i],'连续项为训练流程标准化尺度；二分类为0/1']));
}
table(sheets.Folds,{headers:['model','feature','coefficient','meaning'],rows:coef},24,'ClinicalFinalParameters');sheets.Folds.getRange('C25:C33').setNumberFormat('0.000000');
const sec=sheets.Sensitivity,sm=s.secondary_complete_interval.metrics;
sec.getRange('A1').values=[['完整初始事件资料敏感性分析（次要）']];sec.getRange('A1').format.font={name:'Arial',size:14,bold:true,color:'#20384F'};
sec.getRange('A3:H3').values=[['扫描数',192,'源患者数',142,'肿瘤',145,'治疗改变',47]];
sec.getRange('A5:E8').values=[['模型','ROC AUC','Brier','治疗改变AP','特异度@0.5'],...['M0','M1','prior'].map(k=>[k,sm[k].roc_auc,sm[k].brier,sm[k].ap_treatment_change,sm[k].specificity_treatment_change])];
sec.getRange('A3:H8').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:29,verticalAlignment:'center'};sec.getRange('A5:E5').format=head;sec.getRange('B6:E8').setNumberFormat('0.0000');
sec.getRange('G5').values=[['病例与主分析不同；两模型在本子集使用相同折。']];sec.getRange('G7').values=[['不能用跨人群AUC差评价模型增益；未作独立验证。']];sec.getRange('G5:G8').format.columnWidth=75;
table(sec,d.secondary,11,'ClinicalCompleteIntervalOOF');sec.freezePanes.freezeRows(11);sec.freezePanes.freezeColumns(2);
const scope=sheets.Scope;
scope.getRange('A1:D10').values=[['固定方案/变量','编码或数值','含义','边界'],['年龄','岁','扫描时年龄','连续变量训练折标准化'],['性别','Male=1 / Female=0','出生性别','二分类'],['初始事件间隔','log1p(天数)','初始手术/治疗/诊断至扫描','仅严格扫描前；不是单纯距手术'],['其他扫描前治疗','Yes=1 / No=0','宽泛的既往治疗字段','不解释为特定药物或因果效应'],['间隔缺失标记','缺失=1 / 有值=0','记录缺失模式','非生物学指标；填补仅用训练折'],['C',1,'L2 Logistic固定强度','无调参或类别加权'],['随机种子',20261029,'固定患者分组','两套患者ID均核对'],['固定分类阈值',0.5,'用于本步混淆计数','没有在验证数据上优化'],['验证折数',5,'StratifiedGroupKFold','M0/M1/对照同病例同折']];
scope.getRange('A1:D10').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:40,verticalAlignment:'center',wrapText:true};scope.getRange('A1:A35').format.columnWidth=31;scope.getRange('B1:D35').format.columnWidth=52;scope.getRange('A1:D1').format=head;
table(scope,d.excluded,13,'ClinicalIdentityExclusions');scope.getRange('C13:D18').format.columnWidth=32;
scope.getRange('A21:D27').values=[['MRI技术核查','状态/数值','证据','未完成事项'],['指定FLAIR参数',d.mri.download_parameter_http_status??null,'两份文件下载参数的HTTP状态','参数不是实际数据'],['实际下载文件',0,'实际传输未启动','尚无NIfTI像素'],['HTTP网关','未配置','公开网页配置','客户端HTTP备用机制尚未验证'],['FASP TCP端口',33001,'连接返回OSError/errno=101','本环境无可用传输链路'],['优先病例0001_01','治疗相关改变','官方测试包目录已匹配','先取得FLAIR及后续常规序列'],['优先病例0003_01','肿瘤','官方测试包目录已匹配','解码、几何和统一ROI待验证']];
scope.getRange('A21:D27').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:39,wrapText:true,verticalAlignment:'center'};scope.getRange('A21:D21').format=head;
scope.getRange('A30:C34').values=[['来源','URL','范围'],['TCIA集合','https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/','CC BY 4.0，当前临床v3与分类明细'],['临床v3','https://www.cancerimagingarchive.net/wp-content/uploads/UCSD_PTGBM-clinical-information_v3_2026-12-Mar.xlsx','固定字节SHA256，未改写原数据'],['分类明细','https://www.cancerimagingarchive.net/wp-content/uploads/details_of_negative_cases_TCIA.xlsx','治疗改变明细与完整分组补集'],['数据论文','https://doi.org/10.1038/s41597-025-06499-z','参考诊断并非逐例病理金标准']];
scope.getRange('A30:C34').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:65,wrapText:true,verticalAlignment:'center'};scope.getRange('B30:B34').format.columnWidth=95;scope.getRange('A30:C30').format=head;
const summary=sheets.Summary;
summary.getRange('B2').values=[['ID隔离后的临床模型重验与扩展']];summary.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
summary.getRange('B4:D4').values=[['同一主分析队列','数量','单位']];
const counts=[['纳入扫描',`=COUNTA(${ospan('ID')})`,'次'],['源患者去重',176,'名'],['肿瘤 / 治疗改变',187,'次肿瘤（另51次改变）'],['隔离ID冲突扫描',5,'次'],['初始间隔缺失',`=SUM(${ospan('initial_event_missing')})`,'次']];
summary.getRange('B5:D9').values=counts.map(r=>[r[0],typeof r[1]==='number'?r[1]:null,r[2]]);
counts.forEach((r,i)=>{if(typeof r[1]==='string')summary.getRange(`C${i+5}`).formulas=[[r[1]]];});
summary.getRange('B12:H15').values=[['OOF模型','ROC AUC','95%下限','95%上限','Brier','治疗改变AP','特异度@0.5'],...['M0','M1','prior'].map(k=>[k,m[k].roc_auc,k in ci?ci[k].roc_auc.lower:null,k in ci?ci[k].roc_auc.upper:null,null,m[k].ap_treatment_change,m[k].specificity_treatment_change])];
['M0','M1','prior'].forEach((k,i)=>summary.getRange(`F${i+13}`).formulas=[[`=AVERAGE(${ospan(k+'_squared_error')})`]]);
summary.getRange('B18:F20').values=[['成对M1−M0','差值','95%下限','95%上限','解释'],['ROC AUC',null,ci.M1_minus_M0.roc_auc.lower,ci.M1_minus_M0.roc_auc.upper,null],['Brier',null,ci.M1_minus_M0.brier.lower,ci.M1_minus_M0.brier.upper,null]];
summary.getRange('C19:C20').formulas=[['=C14-C13'],['=F14-F13']];
summary.getRange('F19:F20').formulas=[['=IF(AND(D19<=0,E19>=0),"区间跨0","区间未跨0")'],['=IF(AND(D20<=0,E20>=0),"区间跨0","区间未跨0")']];
summary.getRange('B23:F25').values=[['固定阈值混淆计数','正确治疗改变TN','改变误判肿瘤FP','肿瘤漏判FN','正确肿瘤TP'],['M0',null,null,null,null],['M1',null,null,null,null]];
['M0','M1'].forEach((name,i)=>{let row=24+i,y=ospan('tumor_label'),pred=ospan(name+'_prediction_0_5');summary.getRange(`C${row}:F${row}`).formulas=[[`=COUNTIFS(${y},0,${pred},0)`,`=COUNTIFS(${y},0,${pred},1)`,`=COUNTIFS(${y},1,${pred},0)`,`=COUNTIFS(${y},1,${pred},1)`]];});
summary.getRange('B28:E30').values=[['次要完整间隔分析','扫描数','源患者数','AUC'],['M0',192,142,sm.M0.roc_auc],['M1',192,142,sm.M1.roc_auc]];
summary.getRange('J4:J9').values=[['本步结论'],['扩展临床AUC点估计由0.612升至0.679。'],['成对增益区间跨0，只能称改善趋势。'],['0.5阈值仅识别51次治疗改变中的5次。'],['两套患者ID均无训练/验证交叉。'],['上轮0.575是不同队列/折的历史结果。']];
summary.getRange('J13:J18').values=[['解释限制'],['4项临床变量，另含间隔缺失标记。'],['46次间隔缺失可能反映记录模式。'],['区间条件于固定OOF预测，未做外部验证。'],['完整资料次要分析不能替换主分析。'],['修改Excel不会重新训练Python模型。']];
summary.getRange('J23:J28').values=[['下一步需批准'],['两例实际FLAIR仍未取得，像素质控为0。'],['优先通过官方Aspera获取两例样本。'],['统一ROI不得用TCT/ECT/NECT参考掩膜。'],['MRI比较须在共同病例上重跑临床对照。'],['本步结束，等待用户批准下一阶段。']];
summary.getRange('B4:J30').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:31,verticalAlignment:'center'};
summary.getRange('B4:B30').format.columnWidth=28;summary.getRange('C4:H30').format.columnWidth=22;summary.getRange('I4:I30').format.columnWidth=4;summary.getRange('J4:J30').format.columnWidth=76;
for(const r of ['B4:D4','B12:H12','B18:F18','B23:F23','B28:E28','J4','J13','J23'])summary.getRange(r).format=head;
summary.getRange('C13:H15').setNumberFormat('0.0000');summary.getRange('C19:E20').setNumberFormat('0.0000');summary.getRange('C24:F25').setNumberFormat('#,##0');summary.getRange('E29:E30').setNumberFormat('0.0000');
for(const sh of Object.values(sheets))sh.showGridLines=false;summary.tabColor='#35556D';
wb.recalculate();
if(Math.abs(summary.getRange('F14').values[0][0]-m.M1.brier)>1e-10||summary.getRange('C25').values[0][0]!==5)throw new Error('Main summary reconciliation failed');
const cell=sheets.OOF.getRange(`${ocol('M0_oof_probability')}2`),original=cell.values[0][0],before=summary.getRange('F13').values[0][0];cell.values=[[0]];wb.recalculate();if(summary.getRange('F13').values[0][0]===before)throw new Error('Formula response check failed');cell.values=[[original]];wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!B12:H20',include:'values,formulas',tableMaxRows:9,tableMaxCols:7,maxChars:3500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const [name,range]of [['Summary','B2:J30'],['OOF','A1:H6'],['Folds','A1:J6'],['Sensitivity','A1:H8'],['Scope','A1:D10']]){
 const b=await wb.render({sheetName:name,range,scale:1.1,format:'png'});await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await b.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_Clinical_Revalidation.xlsx'));console.log('Exported clinical revalidation workbook');
