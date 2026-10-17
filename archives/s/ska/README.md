# ska

**SKA (Split Kmer Analysis)** — 细菌基因组流行病学 split-kmer 分析工具箱。

SKA 面向原核（及任何小型单倍体）基因组 DNA 序列分析：split kmer 是一条
DNA 序列中相隔单个碱基的一对 kmer，可用于快速比较与比对小基因组，
特别适合监测（surveillance）与疫情调查（outbreak investigation）场景。
SKA 可从 fasta 组装或 fastq 测序reads直接构建 split kmer 文件，进行聚类、
有/无参考比对，并输出多种比较与汇总统计。

## 用法

```bash
ska <subcommand>

# 子命令
align     无参考的多 split kmer 文件比对
alleles   合并多个 multifasta 为一个 split kmer 文件
annotate  在参考 fasta/gff 中定位/注释 split kmer
compare   查询 skf 与一组目标 skf 的比较统计
distance  成对距离计算与聚类
fasta     从 fasta 文件创建 split kmer 文件
fastq     从 fastq 文件创建 split kmer 文件
info      打印一个或多个 kmer 文件的信息
map       将 skf 比对到参考 fasta
merge     合并多个 skf
summary   打印 skf 汇总统计
type      用等位基因文件对 skf 分型
unique    输出 skf 集合中独有的 kmer
version   打印版本与引用信息
weed      从 skf 中剔除 kmer
```

## 本仓适配

- 版本 1.0，纯 Makefile 构建，链接 zlib（静态，制品仓包）。
- 上游 27 个 gtest 用例在 OHOS aarch64 实机全部通过（详见 1.0/notes.md）。
- test_package 内含鸿蒙消费者端到端用例（fasta→skf→info→gzip 输入→distance）。
