import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.RN_PROJECT_ROOT;if(!root)throw new Error('RN_PROJECT_ROOT is required');
const outputDir=path.join(root,'outputs/ucsd-clinical-baseline-20261029');
const d=JSON.parse(await fs.readFile(path.join(root,'reports/ucsd_baseline_workbook_input.json'),'utf8'));
const s=d.summary,m=s.logistic_oof,q=s.prevalence_only_oof,ci=s.patient_cluster_bootstrap_95ci;
const wb=Workbook.create(),summary=wb.worksheets.add('Summary'),t=wb.worksheets.add('Timepoints'),folds=wb.worksheets.add('Folds');
const letter=n=>{let x='';while(n){n--;x=String.fromCharCode(65+n%26)+x;n=Math.floor(n/26);}return x;};
const n=d.rows.length+1,headers=[...d.headers,'logistic_squared_error','prior_squared_error'];
const col=k=>letter(headers.indexOf(k)+1),range=k=>`Timepoints!${col(k)}2:${col(k)}${n}`;
const headerStyle={fill:'#35556D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:58,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
t.getRangeByIndexes(0,0,n,headers.length).values=[headers,...d.rows.map(r=>[...r,null,null])];
t.getRangeByIndexes(0,0,n,headers.length).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:28,verticalAlignment:'center'};
headers.forEach((key,j)=>{
 const vals=d.rows.map(r=>r[j]).filter(v=>v!==null&&v!==undefined),isText=vals.some(v=>typeof v==='string');
 const r=t.getRangeByIndexes(0,j,n,1);
 r.format.columnWidth=/source$|reason|diagnosis_raw/.test(key)?62:Math.max(20,Math.min(31,key.length*.85));
 r.setNumberFormat(isText?'@':/probability|error/.test(key)?'0.000000':'#,##0');
 t.getRangeByIndexes(1,j,n-1,1).format.horizontalAlignment=isText?'left':'right';
});
for(let row=2;row<=n;row++){
 t.getRange(`${col('logistic_squared_error')}${row}`).formulas=[[`=(${col('tumor_label')}${row}-${col('oof_tumor_probability')}${row})^2`]];
 t.getRange(`${col('prior_squared_error')}${row}`).formulas=[[`=(${col('tumor_label')}${row}-${col('oof_prevalence_only_probability')}${row})^2`]];
}
t.getRangeByIndexes(0,0,1,headers.length).format=headerStyle;
t.tables.add(`A1:${letter(headers.length)}${n}`,true,'UCSDClinicalOOF');t.freezePanes.freezeRows(1);t.freezePanes.freezeColumns(2);
t.getRange('W1:Y5').values=[['来源/定义','URL/说明','SHA256/备注'],
 ['临床v3','https://www.cancerimagingarchive.net/wp-content/uploads/UCSD_PTGBM-clinical-information_v3_2026-12-Mar.xlsx',s.source_sha256.ucsd_ptgbm_clinical_v3_xlsx??s.source_sha256['ucsd_ptgbm_clinical_v3.xlsx']],
 ['negative-case明细','https://www.cancerimagingarchive.net/wp-content/uploads/details_of_negative_cases_TCIA.xlsx',s.source_sha256['ucsd_ptgbm_negative_cases.xlsx']],
 ['官方分组','https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/','243=192残余/复发肿瘤+51治疗改变；CC BY 4.0'],
 ['数据论文','https://doi.org/10.1038/s41597-025-06499-z','保留原文出处；标签不等同逐例病理证实']];
t.getRange('W8:X16').values=[['字段/编码','定义'],['tumor_label=1','由官方完整分组及阴性清单补集推导的肿瘤'],['tumor_label=0','明确列于治疗相关改变清单；不是未来RN阴性'],['age_years / sex_male','年龄单位岁；Male=1，Female=0，均无缺失'],['negative_list_dx / label_source','原始亚型和标签来源，仅作审计，不作为输入'],['diagnosis_text_anomaly','源文本含Grade 5；保留原值，不作预测输入'],['validation_fold / oof_tumor_probability','患者分组验证折；每次扫描的折外肿瘤概率'],['logistic_squared_error / prior_squared_error','真实0/1标签与概率之差的平方，平均即Brier'],['刷新说明','修改表格不会重训模型；须重跑Python和构建器']];
t.getRange('W1:Y16').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:49,wrapText:true,verticalAlignment:'center'};
t.getRange('W1:W16').format.columnWidth=39;t.getRange('X1:X16').format.columnWidth=92;t.getRange('Y1:Y16').format.columnWidth=68;
for(const r of ['W1:Y1','W8:X8'])t.getRange(r).format=headerStyle;
folds.getRangeByIndexes(0,0,6,d.fold_headers.length).values=[d.fold_headers,...d.fold_rows];
folds.getRangeByIndexes(0,0,6,d.fold_headers.length).format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:30,verticalAlignment:'center',columnWidth:22};
folds.getRangeByIndexes(0,0,1,d.fold_headers.length).format=headerStyle;
folds.getRange('H2:M6').setNumberFormat('0.0000');folds.getRange('A2:G6').setNumberFormat('#,##0');
folds.tables.add(`A1:${letter(d.fold_headers.length)}6`,true,'UCSDValidationFolds');folds.freezePanes.freezeRows(1);
folds.getRange('A10:C13').values=[['最终全队列描述参数','数值','解释'],['年龄每10岁OR',s.final_fit_parameters.age_odds_ratio_per_10_years,'不用于独立危险因素或因果推断'],['Male相对Female OR',s.final_fit_parameters.male_vs_female_odds_ratio,'完整参数另存JSON；性能只报告OOF'],['年龄均值 / 标准差',s.final_fit_parameters.age_mean,`SD=${s.final_fit_parameters.age_sd.toFixed(4)}岁`]];
folds.getRange('A10:C13').format={font:{name:'Arial',size:10,color:'#263747'},rowHeight:38,wrapText:true,verticalAlignment:'center'};
folds.getRange('A10:C10').format=headerStyle;folds.getRange('A10:A13').format.columnWidth=27;folds.getRange('C10:C13').format.columnWidth=47;folds.getRange('B11:B13').setNumberFormat('0.0000');
summary.getRange('B2').values=[['高级别胶质瘤治疗后鉴别：临床基线']];
summary.getRange('B2').format.font={name:'Arial',size:15,bold:true,color:'#20384F'};
summary.getRange('B4:D4').values=[['队列与验证','数值','单位']];
const counts=[['纳入扫描',`=COUNTA(${range('ID')})`,'次'],['患者去重',s.patients,'名'],['肿瘤扫描',`=SUM(${range('tumor_label')})`,'次'],['治疗改变扫描',`=COUNTIFS(${range('tumor_label')},0)`,'次'],['肿瘤占比',`=C7/C5`,'比例'],['患者跨类 / 验证折数',s.mixed_class_patients,'名（固定5折）']];
summary.getRange('B5:D10').values=counts.map(r=>[r[0],typeof r[1]==='number'?r[1]:null,r[2]]);
counts.forEach((r,i)=>{if(typeof r[1]==='string')summary.getRange(`C${i+5}`).formulas=[[r[1]]];});
summary.getRange('C9').setNumberFormat('0.0%');
summary.getRange('B12:F12').values=[['OOF指标','年龄+性别','95%下限','95%上限','比例对照']];
const metrics=[['ROC AUC','roc_auc'],['肿瘤类AP','ap_tumor'],['治疗改变类AP','ap_treatment_change'],['Brier（越低越好）','brier']];
summary.getRange('B13:F16').values=metrics.map(([label,key])=>[label,key==='brier'?null:m[key],ci[key].lower,ci[key].upper,key==='brier'?null:q[key]]);
summary.getRange('C16').formulas=[[`=AVERAGE(${range('logistic_squared_error')})`]];
summary.getRange('F16').formulas=[[`=AVERAGE(${range('prior_squared_error')})`]];
summary.getRange('B17:F17').values=[['Brier差（模型−对照）',null,ci.brier_difference_logistic_minus_prior.lower,ci.brier_difference_logistic_minus_prior.upper,null]];
summary.getRange('C17').formulas=[['=C16-F16']];
summary.getRange('B20:F20').values=[['固定0.5阈值','正确治疗改变TN','改变误判肿瘤FP','肿瘤漏判FN','正确肿瘤TP']];
const y=range('tumor_label'),pred=range('oof_prediction_at_0_5');
summary.getRange('B21').values=[['混淆计数']];
summary.getRange('C21:F21').formulas=[[`=COUNTIFS(${y},0,${pred},0)`,`=COUNTIFS(${y},0,${pred},1)`,`=COUNTIFS(${y},1,${pred},0)`,`=COUNTIFS(${y},1,${pred},1)`]];
summary.getRange('B23:E24').values=[['肿瘤敏感度',null,'治疗改变特异度',null],['平衡准确率',null,'总体准确率',null]];
summary.getRange('C23').formulas=[['=F21/(E21+F21)']];summary.getRange('E23').formulas=[['=C21/(C21+D21)']];
summary.getRange('C24').formulas=[['=(C23+E23)/2']];summary.getRange('E24').formulas=[['=(C21+F21)/C5']];
summary.getRange('H4:H11').values=[['结果与解释'],['AUC接近随机；区间跨0.5。'],['固定阈值未识别51次治疗相关改变。'],['年龄、性别不足以形成有效鉴别模型。'],['Brier差的区间跨0，未支持明确增益。'],['标签来自清单与官方分组推导。'],['单中心内部验证，未进行外部验证。'],['本步未下载新队列MRI或提取影像特征。']];
summary.getRange('H14:H18').values=[['验证方法'],['按患者分5折，年龄仅训练折标准化。'],['患者整簇bootstrap 2000次，固定OOF概率。'],['区间不含全部重新训练/划折变异。'],['肿瘤AP必须结合79%的肿瘤占比解释。']];
summary.getRange('H21:H24').values=[['下一步需批准'],['小样本MRI获取、ID和序列质量核查。'],['先确认ROI独立于标签定义且两组可用。'],['本步到此结束，等待用户批准。']];
summary.getRange('B4:H24').format.font={name:'Arial',size:10,color:'#263747'};
summary.getRange('B4:F24').format.rowHeight=32;summary.getRange('B4:B24').format.columnWidth=29;summary.getRange('C4:F24').format.columnWidth=23;summary.getRange('G4:G24').format.columnWidth=4;summary.getRange('H4:H24').format.columnWidth=66;
summary.getRange('H4:H24').format.wrapText=true;
for(const r of ['B4:D4','B12:F12','B20:F20','H4','H14','H21'])summary.getRange(r).format=headerStyle;
summary.getRange('C13:F17').setNumberFormat('0.0000');summary.getRange('C21:F21').setNumberFormat('#,##0');summary.getRange('C23:C24').setNumberFormat('0.0%');summary.getRange('E23:E24').setNumberFormat('0.0%');
for(const sheet of [summary,t,folds]){sheet.showGridLines=false;sheet.tabColor='#35556D';}
wb.recalculate();
// Verify that formulas react to an edited row, then restore the analytical values.
const pcell=t.getRange(`${col('oof_tumor_probability')}2`),original=pcell.values[0][0];
const before=summary.getRange('C16').values[0][0];pcell.values=[[0]];wb.recalculate();
const after=summary.getRange('C16').values[0][0];if(before===after)throw new Error('Brier formula failed input-change check');
pcell.values=[[original]];wb.recalculate();
if(Math.abs(summary.getRange('C16').values[0][0]-m.brier)>1e-10)throw new Error('Brier reconciliation failed');
console.log((await wb.inspect({kind:'table',range:'Summary!B12:F17',include:'values,formulas',tableMaxRows:6,tableMaxCols:5,maxChars:3000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10}})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
for(const [name,sheet,range]of [['Summary','Summary','B2:H24'],['Timepoints','Timepoints','A1:H6'],['Sources','Timepoints','W1:Y5'],['Definitions','Timepoints','W8:X16'],['Folds','Folds','A1:M6'],['Parameters','Folds','A10:C13']]){
 const preview=await wb.render({sheetName:sheet,range,scale:1.1,format:'png'});
 await fs.writeFile(path.join(outputDir,`preview_${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'UCSD_Clinical_Baseline.xlsx'));
console.log('Exported clinical baseline workbook');
