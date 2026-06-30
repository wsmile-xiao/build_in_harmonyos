# gnuplot

gnuplot 是一个便携的命令行驱动的绘图工具，支持多种输出格式和交互式终端。

## 版本

- **5.4.10** (2026-05-26) - 当前版本

## 功能特性

- 二维和三维绘图
- 支持多种输出格式：PNG、JPEG、GIF、PostScript、PDF、SVG、LaTeX 等
- 交互式终端（X11、Qt、wxWidgets、cairo）
- 内置脚本语言支持
- 统计分析和数据拟合
- 支持外部插件

## 编译状态

| 版本 | 状态 | 编译日期 | 预编译包 |
|------|------|---------|---------|
| 5.4.10 | published | 2026-05-26 | ✅ 可用 |

## 平台适配说明

### HMDFS umask 问题 (E011)

gnuplot 使用 autotools 构建系统，configure 脚本在 HMDFS 文件系统上创建临时目录时会遇到权限问题（umask 077 导致创建失败）。

**解决方案**：修改 configure 脚本中的 `umask 077` 为 `umask 022`。

**补丁**：`0001-umask-022-for-hmdfs.patch`

## 可选依赖

以下依赖为可选，不影响基本功能：

- GNU readline - 增强命令行编辑体验
- libgd - PNG/JPEG/GIF 输出支持
- cairo/pango - 高质量矢量图形输出
- Qt - Qt 终端支持
- wxWidgets - wxWidgets 终端支持
- lua - TikZ/LaTeX 终端支持
- libcerf - 特殊函数支持

## 参考链接

- 官网：http://www.gnuplot.info/
- 文档：http://www.gnuplot.info/documentation/
- 源码：https://sourceforge.net/projects/gnuplot/