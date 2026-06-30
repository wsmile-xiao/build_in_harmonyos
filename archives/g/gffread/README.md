# gffread

GFF/GTF format conversions, region filtering, FASTA sequence extraction.

gffread 是一个用于处理 GFF/GTF 注释文件的工具软件，由 Geo Pertea 开发，许可证为 MIT。它可以：
- 在 GFF3 和 GTF 格式之间转换
- 按区域、ID、链方向等条件过滤转录本特征
- 从基因组 FASTA 中提取 exon/CDS 序列
- 转换为 BED12 格式
- 过滤单 exon 转录本、仅保留编码转录本等

论文引用: DOI: 10.12688/f1000research.23297.1

## 版本

| 版本 | 状态 | 日期 |
|---------|--------|------|
| 0.12.7 | published | 2026-06-10 |

## 构建信息

- **构建系统**: makefile (纯 Makefile，无 configure 脚本)
- **编译器**: clang 15.0.4 / clang++ (OpenHarmony 平台)
- **许可证**: MIT
- **依赖**: 无（纯 C++ 项目）
- **补丁**: 1 个 (`0001-Makefile.patch` — 将 CXX/LINKER 默认值从 g++ 改为 clang++)

## 安装

预编译包通过 cmd-pkgs 公共安装脚本部署：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gffread 0.12.7
```

安装后验证：
```bash
gffread --version
# 应输出: 0.12.7
```

## 常见用法

```bash
# GFF3 → GTF 转换
gffread input.gff3 --gtf -o output.gtf

# 区域过滤
gffread input.gff3 -r chr1:1000-5000 -o filtered.gff3

# BED 格式转换
gffread input.gff3 --bed -o output.bed

# 仅保留编码转录本
gffread input.gff3 -C -o coding_only.gff3

# 丢弃单 exon 转录本
gffread input.gff3 -U -o multi_exon.gff3
```