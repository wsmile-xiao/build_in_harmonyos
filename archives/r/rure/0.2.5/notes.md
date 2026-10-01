# rure 0.2.5：HarmonyOS PC 适配

任务类型：目标库适配（路径 A 依赖项）。上游为 Rust `regex` 引擎的 C API（workspace 成员 `regex-capi/`），
以 crates.io `rure 0.2.5` 发布。构建系统为 **cargo**（`crate-type = ["staticlib","cdylib","rlib"]`），
交付 `librure.a` 与 `include/rure.h`。

## 固定源码与依赖

- 源码：https://static.crates.io/crates/rure/rure-0.2.5.crate；SHA256
  `8af70744723e3d5b88fec7869518bbd17883b7d9944f67c9b4a69ae4ed90dc9a`；许可证 MIT OR Apache-2.0。
- crate 内 `.cargo_vcs_info.json`：`sha1=2aaa18dfaeda7a07202f1c8a0d7a7a10116d5153`，`path_in_vcs=regex-capi`。
- Rust 1.97.1 由已发布的官方 Conan 包 `rust-toolchain/1.97.1` 提供（`tool_requires`）。
- OpenSSL DSO：由 `openssl/3.5.6.1.1` 的 PIC 静态归档重链接出 `libssl.so`/`libcrypto.so`，
  仅供 cargo 运行时私有使用（不注入全局或 Conan 公共 lib 目录）。
- crate 依赖（`libc`、`regex`、`regex-automata`、`regex-syntax`、`aho-corasick`、`memchr`）
  由 cargo 从 crates.io/镜像拉取，随工具链编译，非 Conan 包。

## OHOS 平台要点（真机验证）

1. **Rust 工具链签名**：`rust-toolchain/1.97.1` 的 `bin/cargo`、`bin/rustc`、`lib/librustc_driver-*.so`
   在 OHOS 上必须签名才能执行（未签名报 `Permission denied`）。配方在构建目录内对其**私有一份**签名，
   不修改 Conan 依赖包，也不将其重新打包。
2. **cargo 运行库**：cargo 动态依赖 `libssl.so`、`libcrypto.so`、`libz.so`。前两者从 openssl PIC
   静态归档重链接（soname 设为 cargo 需要的裸名）并签名；`libz.so` 为系统 `/usr/lib/libz.so.1` 的签名副本。
3. **clang 包装脚本**：`/data/service/hnp/bin/clang` 是 `#!/bin/sh` 包装脚本，OHOS/conan 无法执行
   shebang 脚本（驱动返回 1 且无输出）。配方解析该包装脚本内容并定位真实 ELF 驱动 `clang-15` 后再调用。
4. **sysroot**：私有 sysroot 经软链不可被 rustc 识别，故通过 `RUSTFLAGS=--sysroot=<rust-toolchain>` 显式指定。

## 原始失败与最小修复

1. `cargo --version` → `Permission denied`：OHOS 拒绝执行未签名 ELF。
   修复：对 cargo/rustc/rustc_driver 私有一份签名。
2. `cargo --version` → `Error loading shared library libssl.so/libcrypto.so`：
   修复：从 `openssl/3.5.6.1.1` PIC 静态归档重链接并签名（`libcrypto.so`、`libssl.so`）。
3. `cargo build` → `can't find crate for 'std'`：rustc 未使用私有 sysroot。
   修复：`RUSTFLAGS=--sysroot=<rust-toolchain>`。
4. conan 内调用 clang 返回 `exit 1` 无输出：`clang` 为 shell 包装脚本，conan 无法执行 shebang。
   修复：解析包装脚本，调用真实 `clang-15`。

## 上游测试

- 入口：`ctest/test.c`（纯 C，链接 `librure.a`）。
- 命令：`clang -O2 -I include ctest/test.c librure.a -o rure_ctest && ./rure_ctest`。
- 结果：**13/13 PASSED，0 failed，0 skipped**。
- 样例：`examples/iter.c` 配 `examples/sherlock.txt` 实际运行成功（输出匹配位置）。
- 用例名：test_is_match, test_shortest_match, test_find, test_captures, test_iter,
  test_iter_capture_names, test_flags, test_compile_error, test_compile_error_size_limit,
  test_regex_set_match, test_regex_set_options, test_regex_set_match_start, test_escape。

## 环境限制（阻塞 conan create 本地 W3）

本机（共享 OHOS 真机）经实测存在以下平台级限制，导致 `conan create` 的 `build()` 内无法调用 clang 驱动：
- conan 进程（以及任何 Spark/HMDFS 上启动的 Python 进程）在**内存压力窗口**下执行 `clang-15`
  会出现 `exit 1` 且无任何 stderr（`ld.lld`/`clang-check`/`clang-format`/`llvm-ar` 等较小 HNP 工具正常）；
  同一命令从 shell 直接执行始终成功。
- 已排除：环境变量（最小 env 同样失败）、cwd、argv[0]、stdout 模式、close_fds、栈限制、SELinux 域
  （conan 与 shell python 均为 `u:r:adhoc_bin:s0`）。
- 症状与系统 free 内存/负载强相关（`Committed_AS` 长期远超 `CommitLimit`）。
- 建议在 Headless Node 的 Linux 环境执行 W3/CI，或在高内存窗口重试。

**最终状态**：配方、test_package、上游测试与文档已就绪；本地手动全流程通过；`conan create` 待环境允许后复跑。
---

**编译结束**: 2026-10-01 15:25
**最终状态**: built
