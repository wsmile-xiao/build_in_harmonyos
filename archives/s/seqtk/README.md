# seqtk

FASTA/FASTQ 序列处理工具，用于生物信息学领域。

## 简介

seqtk 是一个轻量高效的 FASTA/FASTQ 格式序列数据处理工具，由 Heng Li 开发。它提供了多种常用的序列变换和统计功能，包括子采样、子序列提取、质量修剪、核苷酸组成分析等。

seqtk 是单文件 C 程序（seqtk.c），编译极为简单，使用简单 Makefile 构建，无 configure 脚本。

## 许可证

MIT License

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.5 | published | 2026-06-02 | 当前稳定版本，版本号 1.5-r133 |

## 构建信息

- 构建系统：简单 Makefile（无 configure）
- 编译器：clang 15.0.4
- 编译选项：`CC=clang CFLAGS="-fPIC -O2 -g -Wall -Wno-unused-function -Wno-format"`
- 依赖：zlib（系统自带动态库 libz.so）
- 无需补丁即可在 OpenHarmony 上编译

## 使用说明

seqtk 不支持 `--version` 标志。运行 `seqtk` 直接查看使用信息和版本号（显示在 Usage 头部）。

## 支持的子命令

seq、size、comp、sample、subseq、fqchk、mergepe、split、trimfq、hety、gc、mutfa、mergefa、famask、dropse、rename、randbase、cutN、gap、listhet、hpc、telo