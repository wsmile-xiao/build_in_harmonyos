# bwa 0.7.19 适配笔记

## 概述

BWA（Burrow-Wheeler Aligner）是 DNA reads 与参考序列比对的命令行工具。赛事平台任务版本为 `0.7.19`，与 Homebrew stable 版本一致。

## 构建系统

- 构建系统：plain Makefile
- 主要产物：`bwa` 可执行文件
- Makefile 默认值：`CC=gcc`、`AR=ar`、`LIBS=-lm -lz -lpthread`
- ARM 优化：源码已包含 `neon_sse.h`，`ksw.c` 在 `__ARM_NEON` 下包含该本地头文件

## 依赖

- `zlib/1.3.1`：Conan 依赖，提供 `zlib.h` 与 `libz`
- `pthread`、`libm`：系统库

Homebrew 公式中运行依赖为空，构建依赖列出 `sse2neon`；但本次源码预检确认上游 0.7.19 已自带 `neon_sse.h`，因此暂不额外引入 `sse2neon` 包。

## 实际构建命令

```bash
make -j1 \
  CC=<clang> \
  AR=<ar> \
  RANLIB=<ranlib> \
  CPPFLAGS="-I<zlib include>" \
  LDFLAGS="-L<zlib lib> -fuse-ld=/data/service/hnp/bin/ld" \
  bwa
```

`CC`、`AR`、`RANLIB` 均从 Conan conf `tools.build:compiler_executables` 读取；zlib include/lib 路径从 `self.dependencies["zlib"].cpp_info` 读取，不依赖 shell 环境变量。

## 测试策略

上游没有 `make check` 目标。本配方通过 `test_package/test_bwa.sh` 做真实功能验证：

1. 运行 `bwa` usage smoke test。
2. 构造一个极小 FASTA 参考序列。
3. 构造一个 FASTQ read。
4. 执行 `bwa index ref.fa` 并断言索引文件生成。
5. 执行 `bwa aln ref.fa read.fq > read.sai`。
6. 执行 `bwa samse ref.fa read.sai read.fq > aln.sam`。
7. 断言 SAM 中 `r1` mapped 到 `ref`，CIGAR 为 `24M`。

2026-07-17 00:01 CST 复跑结果：

```text
bwa.tar.gz: OK
bwa functional test: PASS
```

## 风险与回滚

- 如果 OHOS worker 上 `__ARM_NEON` 分支出现编译错误，优先检查本地 `neon_sse.h` 与 clang/aarch64 NEON intrinsic 兼容性；必要时再考虑引入 `sse2neon` 或强制 scalar path。
- `bwa --version` / `bwa --help` 不是标准选项，CI L2 可能给出非阻塞 warning；功能测试已经覆盖真实命令链。
- 比赛 CI 已执行 `conan create` 与 `test_package`，验证结果与 `manifest.yaml` 中的 `test_results` 保持一致。

## CI 复跑记录

- 2026-07-17 19:54 CST：CI #6613（Worker `OpenHarmonyPCDeveloper-CI-012`）校验通过，`conan-build-test` 执行成功，`Conan test_package` 已执行，L0 结构完整性与 L1 测试执行验证均通过。
