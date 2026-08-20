# ctags — Universal Ctags

## 软件简介

Universal Ctags（u-ctags）是一个维护中的 ctags 实现，用于为源代码文件中的语言对象生成索引（标签）文件。它是 Exuberant Ctags 的继任者，支持 150+ 种编程语言。

ctags 生成的标签文件可被 Vim、Emacs 等编辑器用于代码导航，支持快速跳转到函数、类、变量等定义位置。

- **主页**: https://ctags.io/
- **源码**: https://github.com/universal-ctags/ctags
- **许可证**: MIT

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|---------|---------|
| 6.2.1 | built | 2026-07-06 | autotools |

## 产物

| 文件 | 说明 |
|------|------|
| ctags | 主程序，生成标签文件 |
| readtags | 标签文件读取/查询工具 |
| optscript | 内嵌脚本解释器 |

所有二进制均为静态链接，适用于 OpenHarmony (aarch64) 平台。
