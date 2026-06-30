# bioawk

> 生物信息学 awk 工具

## 简介

bioawk 是 Heng Li 开发的基于 BWK awk（One True Awk）的生物信息学 awk 扩展版本。它在标准 awk 的基础上增加了对常见生物信息学文件格式（FASTA、FASTQ、SAM、VCF、GFF、BED）的内建支持，使用户可以用简洁的 awk 语法处理序列数据。

## 主要特性

- 完整兼容 BWK awk 语法
- 内建 FASTA/FASTQ/SAM/VCF/GFF/BED 格式解析（`-c fastx`、`-c sam` 等）
- 支持 `$name`、`$seq`、`$qual` 等生物学字段变量
- 支持序列操作函数（`revcomp`、`and`、`or`、`xor` 等）

## 安装

```bash
# 通过 cmd-pkgs 预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- bioawk 1.0
```

## 用法示例

```bash
# 统计 FASTA 序列长度
bioawk -c fastx '{print $name, length($seq)}' input.fa

# 解析 FASTQ
bioawk -c fastx '{print $name, $seq, $qual}' input.fq

# 计算 GC 含量
bioawk -c fastx '{s=$seq; gsub(/[^GC]/, "", s); gc=length(s); print $name, gc/length($seq)*100}' input.fa
```

## 编译信息

| 项目 | 值 |
|------|-----|
| 版本 | 1.0 |
| 构建系统 | 纯 Makefile（BWK awk fork） |
| 编译器 | clang 15.0.4 |
| 依赖 | zlib |
| 平台 | HarmonyOS aarch64 (musl) |
| 预编译包 | bioawk-1.0-ohos-aarch64.tar.gz |

## 许可证

基于 Lucent Technologies BWK awk 许可证（BSD 风格）。
