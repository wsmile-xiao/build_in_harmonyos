# cflow

GNU cflow — 分析 C 源代码并生成调用图的工具。

## 基本信息
- **版本**: 1.8
- **许可证**: GPL-3.0-or-later
- **构建系统**: autotools
- **源码 URL**: https://ftpmirror.gnu.org/gnu/cflow/cflow-1.8.tar.bz2
- **描述**: Generate call graphs from C code

## 功能
- 从 C 源代码生成直接和反向调用图
- 支持多种输出格式（gnu、posix、dot）
- 支持递归调用检测、属性处理、结构体分析
- 支持 K&R 和 ANSI C 函数声明

## 依赖
- 无外部库依赖

## OpenHarmony 适配
- 需替换 build-aux/config.guess 和 config.sub 为 automake-1.16 版本（E007）
- HMDFS 限制：需修改 config.status 的临时文件机制（umask 077 → 000，路径 ./ → $TMPDIR）
- 46/46 测试全部通过