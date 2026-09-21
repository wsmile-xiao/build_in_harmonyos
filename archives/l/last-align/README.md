# LAST (last-align)

LAST 是一款大规模基因组序列比对软件，提供 lastdb/lastal/last-split/last-pair-probs
等命令行工具，用于 DNA/蛋白质序列的比对、索引构建和结果分析。

- 上游: https://gitlab.com/mcfrith/last
- 许可证: GPL-3.0-or-later
- 当前适配版本: 1652

## 工具

| 命令 | 说明 |
|------|------|
| lastdb | 构建比对索引 |
| lastal | 序列比对 |
| last-split | 比对结果拆分（多比对/成对比对）|
| last-pair-probs | 配对读长距离估计 |
| last-merge-batches | 合并比对批次 |
| maf-convert / maf-cut / maf-linked / maf-swap | MAF 格式处理辅助工具（Python 脚本）|
| last-train | 训练替换矩阵（Python 脚本）|
