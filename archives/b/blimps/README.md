# blimps

BLIMPS（BLocks IMProved Searcher）是 FHCRC 开发的 Blocks 蛋白质基序数据库搜索与
Block Maker 生信命令行工具套件，包含 `blocks_search`、`blimps`（序列 vs Blocks
数据库搜索）、`codehop`（简并 PCR 引物设计）、`motifj`/`motomat`（Block 构造）、
`blkprob`/`blksort`（搜索结果分析）等约 49 个工具。license 为 FHCRC
non-commercial（非商业授权）。

当前适配版本：

- `3.9`：plain Makefile 构建（`blimps/Makefile.Linux` + `protomat/Makefile.Linux`），
  仅依赖 libc/libm，打包全部可执行文件与 `share/blimps/docs/` 运行时数据表
  （frequency/scoring/codon usage，工具从工作目录加载）。

使用提示：工具将配置/数据文件路径解析到固定长度缓冲区，请在其工作目录内使用
短文件名（可从包内 `share/blimps/docs/` 复制所需数据表，如 `default.amino.frq`、
`default.qij`、`arab.codon.use`）。
