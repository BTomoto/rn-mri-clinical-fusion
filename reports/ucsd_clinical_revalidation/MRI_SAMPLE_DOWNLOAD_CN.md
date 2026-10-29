# 两例MRI技术样本获取清单

本项目目前已取得公开目录和指定文件的下载参数，尚未取得实际NIfTI。临床分析已独立完成；影像解码/ROI核查需要下面两例真实文件。

1. 打开[UCSD-PTGBM官方集合页](https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/)，在当前版本的Data Access中选择 **BraTS-GLI 2024 Test Data** 下载入口。
2. 按官方网站提示使用IBM Aspera Connect。它是本地传输客户端；本项目执行环境目前没有该客户端且无法连接FASP端口。若本地已有客户端，可直接使用。不需要把个人账号或密码交给本项目。
3. 在`UCSD-PTGBM-BraTS-2024-test-set`中选择`UCSD-PTGBM-0001_01`（治疗相关改变，临床PsP）和`UCSD-PTGBM-0003_01`（推导肿瘤标签）两个目录。两目录名已与临床表匹配，仅供技术核查，不作为效果验证样本。
4. 最小第一批可以仅下载下表的两份FLAIR，用于验证文件读取及几何。后续ROI核查优先补充同目录T1pre、T1post、T2、ADC_vendor和普通BraTS分割，以及官方分割标签说明。无需先下载完整约45 GB队列。

| 源病例 | 第一批实际文件名 |
| --- | --- |
| UCSD-PTGBM-0001_01 | UCSD-PTGBM-0001_01_FLAIR.nii.gz |
| UCSD-PTGBM-0003_01 | UCSD-PTGBM-0003_01_FLAIR.nii.gz |

扩展文件后缀分别为`_T1pre.nii.gz`、`_T1post.nii.gz`、`_T2.nii.gz`、`_ADC_vendor.nii.gz`、`_BraTS_tumor_seg.nii.gz`。保留原始文件名；可以将两病例目录打包后提供。需要的是实际`.nii.gz`内容，网页、下载参数或符号链接清单不能代替体素文件。

下载后本项目将检查文件头/像素可读性、维度/仿射、跨序列一致性及ROI两组适用性。细胞性肿瘤参考掩膜TCT/ECT/NECT不作为本鉴别任务的预测输入。

如本地FASP也受限，IBM Connect有HTTP备用传输机制，但它需要服务端支持，不能由“网页无HTTP网关”推断其必定可用或不可用；本项目尚未验证这一备用路径。[IBM官方网络设置说明](https://www.ibm.com/docs/en/aspera-connect/4.2.x?topic=configuration-network)。未成功取得实际文件前，不把样本标记为下载或质控完成。
