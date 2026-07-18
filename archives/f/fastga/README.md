# FASTGA

FASTGA 是 Gene Myers 等开发的快速基因组比对器及配套 GDB、GIX、ALN、ANO 数据处理工具集。

## OpenHarmony 适配

- 上游使用普通 Makefile，构建 25 个命令行程序。
- 依赖已发布的 `zlib/1.3.1`，另使用系统 pthread 与 libm。
- OpenHarmony libc 无 `rindex()`，适配为标准 `strrchr()`。
- ONElib 临时 schema 使用 `$TMPDIR`，避免只读 `/tmp`（E002）。
