# ncview

ncview 是 netCDF 科学数据文件的交互式可视化浏览器（David W. Pierce,
Scripps Institution of Oceanography）。通过 X11 / Athena widget（Xaw）
界面浏览文件的维度、变量、数值范围与帧动画，是海洋/气象数据处理中
最常用的 netCDF 快速查看工具。

- 官方主页: https://cirrus.ucsd.edu/~pierce/ncview/
- 许可证: GPL-3.0-or-later
- 构建系统: autotools

## 本仓适配

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.1.11 | conan 配方 | vendored libXmu/libXaw/udunits，configure 检测块直接注入 |
