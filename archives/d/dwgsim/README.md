# dwgsim

## 简介

dwgsim（Distribution Wrapped Genome SIMulator）是面向新一代测序数据的**短读段模拟器**：
给定参考 FASTA 与变异参数，生成成对 FASTQ 读段（同时输出 bfast/bwa 两种比对格式与
变异的 txt/vcf），并附带 `dwgsim_eval` 用于评估比对结果的准确率。

- 上游：https://github.com/nh13/DWGSIM
- 许可：GPL-3.0-only
- 构建系统：裸 GNU Makefile（无 configure、无 install 目标）
- 产物：`bin/dwgsim`、`bin/dwgsim_eval`（命令行工具，无库、无头文件）

## OHOS 适配要点

- 上游 `.gitmodules` 声明 `samtools/` 为子模块，**tag 归档里该目录是空的**
  （上游 INSTALL 明确要求 `git submodule update`）。配方按该 tag 树固定的
  gitlink commit `28391e5898804ce6b805016d8c676fdf61442eb3` 取 samtools 官方归档作第二源。
- Makefile 默认目标 `all-recur` 会把依赖 ncurses 的 samtools 主程序一起编出来，
  故显式以 `make dwgsim dwgsim_eval` 构建，只走 `lib-recur`（`libbam.a` + DWGSIM 对象）。
- `PACKAGE_VERSION` 必须作为带引号的 C 字符串进预处理，命令行 DFLAGS 里写
  `-DPACKAGE_VERSION=\"0.1.14\"`（裸引号会被配方 shell 吃掉）。
- 上游硬编码 `CC=gcc`，改由 Conan profile 提供编译器（R33）。
- `-lz` 走 Conan `zlib/1.3.1`，include/lib 绝对路径并入 `CFLAGS`（上游链接行
  是 `$(CC) $(CFLAGS) -o $@ ... -lz`，没有 LDFLAGS 可挂）。
- `make test` 写死 `/bin/bash testdata/test.sh`，OHOS 无该路径，配方改用 PATH
  中的 `bash` 执行同一脚本（脚本零修改）。
- OHOS 上对安装后的 ELF 就地签名，否则消费者测试无法执行。

## 依赖

- 运行/链接：`zlib/1.3.1`
- 源码：`samtools`（上游子模块，固定 commit）

## 参考

- https://github.com/nh13/DWGSIM
- https://github.com/samtools/samtools
