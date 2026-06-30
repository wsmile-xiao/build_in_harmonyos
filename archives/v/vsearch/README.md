# vsearch

## 软件简介

vsearch 是一个开源的微生物组分析工具，用于处理高通量测序数据。它提供了多种功能，包括序列聚类、去重复、搜索、比对等。

- **主页**: https://github.com/torognes/vsearch
- **许可证**: BSD-2-Clause OR GPL-3.0-or-later
- **语言**: C++

## 主要功能

- 序列聚类和去重复
- FASTA/FASTQ 文件处理
- 嵌合体检测
- 序列比对和搜索
- 多序列比对

## 编译版本

| 版本 | 状态 | 编译日期 | 预编译包 |
|------|------|---------|---------|
| 2.30.5 | built | 2026-06-08 | vsearch-2.30.5-ohos-aarch64.tar.gz |

## 使用方式

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- vsearch 2.30.5

# 验证安装
vsearch --version
```

## 注意事项

- 支持 gzip 和 bzip2 压缩文件（需要相应库）
- 使用 SIMD 优化（ARM NEON）