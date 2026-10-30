# 论文必要数据压缩包

本文件夹存放论文Revision 1所需的精简数据快照。

- **[UCSD_Manuscript_Essential_Data_20261030.zip](UCSD_Manuscript_Essential_Data_20261030.zip)**：1.73 MB，65个文件。
- [MANIFEST.json](MANIFEST.json)：逐文件大小、SHA256、来源路径与Git blob SHA。
- [verification.json](verification.json)：样本、指标及压缩包校验结果。

压缩包含两份原始临床Excel工作簿、公开镜像参与者元数据、182次检查/135名患者的完整模型输入和MRI特征、患者分组、折外预测、补充分析数据，以及数据字典和Jupyter核验notebook。MRI体素文件通过546项来源清单保存地址和哈希，便于按需获取。

解压后先阅读包内README.md。需要核验时运行 `python verify_package.py`，或打开 `Verify_Essential_Data.ipynb`。本次整理没有修改标签、特征、预测或论文结果。

来源快照：[`73f04f53c42257a7c45a64aaa96066d8dc61660f`](https://github.com/BTomoto/rn-mri-clinical-fusion/tree/73f04f53c42257a7c45a64aaa96066d8dc61660f)。
打包脚本：[`scripts/package_ucsd_essential_data.py`](../../scripts/package_ucsd_essential_data.py)。

当前数据包支持临床来源核对、特征级模型重分析和论文结果核对。从图像重新提取特征时，按包内影像清单获取对应图像。
