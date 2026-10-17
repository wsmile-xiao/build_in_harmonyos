# MAFFT

> Multiple sequence alignment program for amino acid or nucleotide sequences

## 简介

MAFFT（Multiple Alignment using Fast Fourier Transform）是一个广泛使用的多序列比对
工具，由 Kazutaka Katoh 开发。它提供了多种比对策略，从快速的渐进式方法
（FFT-NS-2）到高精度的迭代细化方法（L-INS-i、G-INS-i），适用于蛋白质、DNA 和 RNA
序列的大规模比对分析。

MAFFT 核心为纯 C 实现，使用 FFT 加速相似度计算，支持多线程。主入口 `mafft` 是一个
bash 脚本，按算法策略分派到内部二进制程序。

- 上游官网：https://mafft.cbrc.jp/alignment/software/
- 许可证：BSD-3-Clause（without-extensions 版本）
- 类型：命令行工具（tool）

## 版本

| 版本 | 状态 | 适配路径 |
|------|------|----------|
| 7.525 | built | archives/m/mafft/7.525 |
