# miniprot

> Align proteins to genomes with splicing and frameshift

## 简介

miniprot（作者 Heng Li）将蛋白质序列比对到基因组上，在比对中建模剪接信号
（内含子两端 GT..AG 等位点）与移码，可从基因组中直接找到蛋白质对应的基因结构
（外显子-内含子组织），输出 PAF（默认）或 GFF3（`--gff`）格式。常用于跨物种
基因注释、同源基因结构预测、基因模型校正。

核心为纯 C99 实现，内嵌 klib（kseq/khashl/ksort 等），氨基酸比对使用 SSE 加速
的动态规划（nasw-sse.c），支持多线程索引构建（kthread）。

- 上游仓库：https://github.com/lh3/miniprot
- 上游主页：https://lh3.github.io/miniprot/
- 许可证：MIT
- 类型：命令行工具（tool）

## 版本

| 版本 | 状态 | 适配路径 |
|------|------|----------|
| 0.18 | built | archives/m/miniprot/0.18 |

## 依赖

- zlib/1.3.1（读 .fa / .fa.gz 输入）
