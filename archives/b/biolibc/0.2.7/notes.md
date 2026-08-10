# biolibc 0.2.7

## 状态

- 状态: adapted
- 类型: static library
- 源码: https://github.com/auerlab/biolibc
- 上游 tag: 0.2.7

## 适配说明

- 使用上游 Makefile 构建 `libbiolibc.a`，不构建 shared library。
- 依赖 `libxtend/0.2.1`，并在 `package_info()` 里传递给消费者。
- 构建期生成 `sysexits.h`，用于 OHOS 系统缺少 BSD `sysexits.h` 的情况。
- OHOS 构建显式映射 `strlcpy/strlcat` 到 libxtend 的 `xt_strlcpy/xt_strlcat`。
- OHOS 下 `tmpfile()` 会尝试不可写的 `/tmp`，`bl_vcf_skip_meta_data()` 等路径未检查 NULL 会导致消费者崩溃；recipe 通过 `-include` 注入 `$TMPDIR` 感知的 `mkstemp + unlink + fdopen` fallback。

## 测试说明

- 上游 Makefile 的 `test` target 指向 `Bed-test/run-test.sh`，但 tag 0.2.7 中实际文件名为 `Bed-test/test.sh`；recipe 不调用这个损坏的顶层 target，改为直接执行 5 个上游 shell 测试入口的等价命令。
- 已在 build 阶段编译并运行 `Bed-test/test.sh`、`Fasta-test/test.sh`、`Fastq-test/test.sh`、`GFF-test/test.sh`、`ORF-test/test.sh` 对应的测试程序和 fixture diff，5/5 通过。
- 测试编译时生成 `test-include/biolibc/*.h`，匹配 Conan 包安装后的 `<biolibc/...>` include 布局。
- `GFF-test/gff-test.c` 来自旧 `gff` API 写法，tag 0.2.7 实际导出 `gff3` API；recipe 仅在 build-local 测试源码中把该测试切到 `gff3` 符号，并补 `bl_gff3_init()`/`bl_gff3_free()`。
- test_package 编译并运行消费者程序，调用 `bl_chrom_name_cmp()`，并通过 `bl_vcf_skip_meta_data()` 覆盖 OHOS `$TMPDIR` 临时文件 fallback。

## OHOS Validation

- Date: 2026-08-09, SSH port 33332, isolated job `ad2vcf-deps-upstream-20260809-r1`.
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-biolibc-deps-upstream-biolibc-r4-20260809-055839-39508`.
- Full package reference: `biolibc/0.2.7#ce95827db17822d034060486f5837b9a:a4bb9bf6232620867f94106b3984a095c1c7f2f8#0b5074eb8aa832e6c77c2e6d9117f15d`.
- Dependency ref: `libxtend/0.2.1#518375c9b2b56e3d5393a71846a836ff:f23d5a9b1d537641c03c7814478a2fadb727650a#30efeec57878d83467f040f1b7e7aae4`.
- CI gates: L0 pass, L1 pass, L2 skip (library package), L4 pass, L5 pass.
- Upstream tests executed: 5/5, passed 5/5. Added consumer/API smoke executed and passed.
