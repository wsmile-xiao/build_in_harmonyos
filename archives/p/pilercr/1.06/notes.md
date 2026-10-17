# pilercr 1.06 适配笔记

## 来源和环境

- 官方源码：`https://www.drive5.com/pilercr/pilercr1.06.tar.gz`，本地 SHA256 `50175f7aa171674cda5ba255631f340f9cc7f80e8cc25135a4cb857147d91068`。
- 构建：上游手写 Makefile；Conan 2.29.1，OHOS clang++、aarch64-linux-ohos，x86_64 runner。无外部 Conan 依赖。
- 上游在 `usage.cpp` 声明 public domain；源码包同时包含过时的预编译 `pilercr`，配方用 `make -B` 强制从源码重建。
- tarball 条目始于 `./pilercr1.06/`，Conan `get(strip_root=True)` 只去掉 `./`，配方手动搬平唯一子目录才应用补丁。

## 编译与补丁

1. NDK clang++ 编译源代码时设置 `-Wno-register`（`E293`，上游 `comp.cpp` 含 C++17 禁用的 `register`）。历史警告 `char*` 字符串常量不影响运行。
2. `patches/0001-Makefile.patch` 只将 `strip pilercr` 改为 `$(STRIP) pilercr`。首次配方用 `realpath(cxx)` 查找目标 llvm-strip，本地通过，但 PR #13010 CI 的另一套 NDK 缺该工具，L1 报 `Invalid configuration: OHOS target llvm-strip missing`。剥离非构建所必需，最终 OHOS 配方传 `STRIP=:` 跳过可选步骤，避免依赖 CI 未安装的剥离器或误用宿主 strip（草稿 `E6402`）。
3. 构建使用目标编译器、Conan Toolchain CXXFLAGS，OHOS 下静态链接；其余环境只使用 `-lm`。不捎带依赖、不修改其他包。

## R51 上游测试清点

- 官方 tar 中 `tests/`、`test/` 目录数均为 0；Makefile 仅 `all`、`pilercr` 和编译规则，无 ctest/pytest 注册。
- `make -n check` 返回 2：`make: *** No rule to make target 'check'. Stop.`。上游测试 N=0，不可伪报 0/0 为 100%。
- 新增一项真实消费者测试（`test_package/consumer.cpp`、`crispr.fa`、`conanfile.py`）：Conan 消费本包静态 OHOS CLI，qemu-aarch64 运行工具解析输入中的多 spacer CRISPR 阵列，生成报告；从报告生成 `discovered.h` 参与 OHOS C++ 编译，再通过 qemu 运行消费者并复核阵列位置、拷贝数、共识重复序列、阵列及 spacer 长度。上游 N=0、适配后鸿蒙特有 N=1。

## 本地验证

- 探索构建：NDK clang++ 编译、链接 `pilercr`，Makefile 原始宿主 strip 失败；本地目标 `llvm-strip` 成功，但 CI 不提供该工具，最终明确禁用非必要 strip。`qemu-aarch64 /root/tmp/pilercr-static -version` 返回 0（`pilercr v1.06`）；动态 ELF 因缺 `/lib/ld-musl-aarch64.so.1` 未当作交付验证。
- 最终 Conan 包是静态 OHOS ELF，不是只测同源 `.o` 的副本：`conan-verify` G2 PASS，`conan create` 日志中 qemu 执行**已打包的 pilercr**、编译消费者、qemu 执行 `consumer`；输出 `OHOS pilercr consumer PASS: array at 401, 7 repeats, consensus GTTCACTGCCGTACAGGCAGCTTAGAAAA`，退出码 0。上游 0/0（无用例）；新增 1/1，通过率 100%，qemu 实跑。
- `test_package/MANIFEST.yml` 记录同一 N=1；`reports/test-report.md` 记录执行证据。

## 注意

上游曾无测试，未改写上游测试；源代码仅 Makefile 一行补丁。与既有 `DRAFT-yosys-0.66-makefile-install-host-strip-cross-elf` 查重后，草稿 `E6402` 专门补充 CI SDK 缺目标剥离器时如何安全跳过可选 strip 的场景。`reports/` 属本地门禁产物，不提交 PR。
---

**编译结束**: 2026-09-26 10:02
**最终状态**: built
