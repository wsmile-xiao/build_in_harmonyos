# R（r-base）HarmonyOS 适配

R 是用于统计计算、数据分析和图形处理的语言解释器与运行环境。

## 功能概述

- R 与 Rscript 命令行解释器
- 基础包、统计计算、矩阵与 BLAS/LAPACK 能力
- PCRE2 正则、压缩、编码转换和网络下载支持

## OHOS 适配

R 的构建会运行刚生成的解释器和 R 脚本，因此采用 OHOS aarch64 设备原生构建。构建及临时目录位于 `/data/storage/el2/base`，并通过 `flang-ohos` 提供 Fortran 编译器。首版关闭缺少设备闭环的 X11、Tcl/Tk、Java、readline、recommended packages 和可选图形依赖。

## 依赖关系

运行依赖为 zlib 1.3.1.1、PCRE2、bzip2、xz、libiconv 和 curl；构建依赖为 flang-ohos。

## 参考资料

- https://www.r-project.org/
- https://cran.r-project.org/src/base/R-4/
