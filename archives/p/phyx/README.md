# phyx

phyx 是一组面向系统发育研究的命令行工具，可处理序列比对、系统发育树、连续性状和祖先状态等数据。

## 功能概述

- 提供序列格式转换、清洗、拼接、重编码与统计工具
- 提供系统发育树转换、修剪、重根、组合与拓扑生成工具
- 提供序列模拟、连续性状分析和祖先状态重建工具
- 以独立 CLI 组成可组合的 Unix 数据处理流程

## HarmonyOS 适配

- 使用 HarmonyOS clang/clang++ 与 Conan Autotools 工具链原生构建。
- 为 GNU `config.guess` 补充 HarmonyOS 原生识别，不用 `--host/--build` 伪装交叉编译。
- 让手写 Makefile 的最终链接线消费 Autoconf 探测结果，保持 Armadillo/OpenBLAS 单一数学后端。
- 联合检查 ELF 动态依赖与普通符号表，防止静态 reference BLAS/LAPACK 与动态 OpenBLAS 双提供者回归。
- 执行完整上游测试，并以固定输入补充确定性数据和 HarmonyOS 运行时闭包测试。

## 依赖关系

- 编译依赖：`automake/1.18`
- 运行依赖：`armadillo/12.8.4`、`nlopt/2.11.0` 及其已发布传递依赖

## 参考资料

- 上游仓库：https://github.com/FePhyFoFum/phyx
- 上游版本：https://github.com/FePhyFoFum/phyx/releases/tag/v1.3.2
- 项目论文：https://doi.org/10.1093/bioinformatics/btx063
