# minimap2

通用的基因组核苷酸序列双序列比对工具。

## 简介

minimap2 是一款通用序列比对程序，在长读段映射的准确性和速度方面可与其他长读段比对工具相当甚至更优。它支持以下应用场景：
- PacBio 或 Oxford Nanopore 基因组读段比对（map-pb、map-ont）
- PacBio Iso-Seq 或 Nanopore cDNA/DNA 直接 RNA 测序读段比对（splice）
- 短基因组读段比对（sr）
- 组装序列间比对（asm5、asm10、asm20）

## 技术信息

- **许可证**：MIT
- **编程语言**：C
- **构建系统**：Makefile（纯 Makefile，非 autotools）
- **SIMD 支持**：aarch64 平台使用 NEON（通过 sse2neon 头文件翻译实现）

## 构建配置

在 aarch64/ARM64 平台上，minimap2 应使用以下参数构建：
```
make arm_neon=1 aarch64=1 CC=clang AR=llvm-ar
```

该参数启用 NEON SIMD 代码路径，通过 sse2neon 头文件实现 SSE2→NEON 指令翻译。