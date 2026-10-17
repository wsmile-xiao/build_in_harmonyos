# biolibc

## 简介

biolibc is a small C library for bioinformatics file formats and helper routines, including BED, FASTA, FASTQ, GFF3, SAM, and VCF helpers.

## OHOS 适配

- 上游使用 Makefile，recipe 仅构建静态库 `libbiolibc.a`。
- 依赖 `libxtend/0.2.1` 提供 DSV、string、memory 等基础工具函数。
- OHOS 构建时生成构建期 `sysexits.h` 兼容头，解决系统缺少 BSD `sysexits.h` 的情况。
- OHOS 下通过 `-Dstrlcpy=xt_strlcpy -Dstrlcat=xt_strlcat` 使用 libxtend 提供的 BSD string 函数实现。

## 依赖

- libxtend/0.2.1

## 功能验证

test_package 编译并运行消费者程序，调用 `bl_chrom_name_cmp()` 验证头文件、静态库和传递链接可用。

