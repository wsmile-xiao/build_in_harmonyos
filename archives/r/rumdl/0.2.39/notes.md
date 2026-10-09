# rumdl 0.2.39 — 适配笔记（HarmonyOS PC / aarch64）

## 1. 软件与源码

| 项 | 值 |
|----|----|
| 名称 | rumdl（Ru(st) MarkDown Linter，Markdown linter + formatter） |
| 版本 | 0.2.39（crates.io 2026-07-21；GitHub tag `v0.2.39` = commit `90648c4194f791f454a599c39628c3752b7b3be5`） |
| 上游 | <https://github.com/rvben/rumdl> |
| 语言 | 纯 Rust（edition 2024，MSRV 1.94.0）/ Cargo |
| 许可证 | MIT |
| 源码包 | `https://github.com/rvben/rumdl/archive/refs/tags/v0.2.39.tar.gz` |
| sha256 | `34791c687b2c9fde08125a6de4b748ea7dfb1765a9984179ac711d895bf72d8d` |
| 产物 | `bin/rumdl`（可执行 + 库；`commands.json` 在软件级目录，R38） |

## 2. 依赖检查（W0）

`Cargo.toml` 依赖全为 crates.io crate，**无 C/C++ 目标依赖**（依赖闭包无外部 C 库 `-sys` crate）。
conan 层唯一需消费的强制第三方依赖是构建工具链 **`rust-toolchain/1.97.1`**（`tool_requires`，可消费，
`conan download` EXIT=0）。`tikv-jemalloc-sys` / `blake3` 为 crate 内置 C 源码，经 `cc` 就地编译。

## 3. 语言预检（R47）

```
$ ohc-run.py lang-preflight rumdl 0.2.39 --src <src> --lang rust
✅ 语言匹配: task=rust, detected=rust
  build_system=cargo, manifest="Cargo.toml name = \"rumdl\"",
  source_stats=577 文件（rust:566/python:11/bash:10，主体占比 98%）
```

## 4. 构建方式

纯 cargo 工程，OHOS aarch64 为**原生宿主三元组**（`aarch64-unknown-linux-ohos`），
`cargo build --release --locked --target aarch64-unknown-linux-ohos --bin rumdl`；链接器 =
OHOS SDK `aarch64-unknown-linux-ohos-clang`。crate 走 `rsproxy.cn` sparse 镜像。

## 5. 实际执行的首个错误、根因与最小修改

### 5.1 工具链（rust-toolchain/1.97.1）二进制不可执行（HMDFS）

- **现象**：包内 `bin/cargo` 直接执行报 `permission denied`（EXIT=126）；`rustc` 另需
  `librustc_driver-*.so` 与 `libc++_shared.so`，未签名 `.so` 在 OHOS 上无法加载（EACCES）。
- **根因**：rust-lang 官方 dist tarball 二进制无 code signature，HMDFS 下 chmod 亦不完全生效。
- **最小修改**：把 `cargo`/`rustc` 及 `librustc_driver-*.so` 复制到 build 目录并用
  `binary-sign-tool -selfSign 1` 自签；`libc++_shared.so`（取自 OHOS SDK）同样复制 + 签名后入
  `LD_LIBRARY_PATH`。

### 5.2 cargo 运行期缺 OHOS 版 `libssl/libcrypto/libz`

- **现象**：`Error loading shared library libssl.so`（cargo 动态链接 libssl/libcrypto/libz）。
- **根因**：OHOS loader 忽略 DT_RUNPATH；系统 `/usr/lib` 是 glibc 版，与 musl cargo 不兼容。
- **最小修改**：使用 Harmonybrew OHOS bottle（`openssl@3-3.6.4_1`、`zlib-ng-compat-2.3.3_2`，sha256 实测）
  解包后入 `LD_LIBRARY_PATH`（argc/1.24.0、rudof/0.3.6 先例）。

### 5.3 首个真实编译错误：`tikv-jemalloc-sys` 的 `config.sub` 不认识 `ohos`

- **现象**（conan create 首次失败，rc=101）：
  ```
  configure: error: /bin/sh build-aux/config.sub aarch64-unknown-linux-ohos failed
  Invalid configuration `aarch64-unknown-linux-ohos': OS `ohos' not recognized
  thread 'main' panicked at tikv-jemalloc-sys-0.6.1+.../build.rs:411
  ```
- **根因**：jemalloc 内置 autotools `config.sub` 早于 `ohos`，`configure --host=aarch64-unknown-linux-ohos`
  时无法规范化三元组。`tikv-jemallocator` 在非 msvc/non-wasm（含 OHOS）为**默认全局分配器**，不可关闭。
- **最小修改**：预置 autoconf 规范化三元组缓存——在构建环境导出
  `ac_cv_build=ac_cv_host=ac_cv_target=aarch64-unknown-linux-musl`，使 `configure` **跳过** `config.sub`
  直接采用缓存值（OHOS 即 musl Linux），**不修改上游源码、不打补丁、不注入 `__OHOS__` 宏**。

### 5.4 第二个错误：`config.status` 在 HMDFS 上无法写临时目录

- **现象**：autoconf 生成的 `config.status` 在 HMDFS 上无法建立临时目录——报无法在 `./confXXXXXX`
  下创建 `subs1.awk`（Permission denied），进而中止于 "config files machinery" 阶段。
- **根因**（知识库 E011/E112）：HMDFS 将目录 owner UID 映射为 20001006，而进程实际 UID 不同；
  toybox `mktemp -d`（autoconf 的 `umask 077 && mktemp -d ./confXXXXXX`）生成 `drwx--S---`(2700)，
  进程无法写入（chmod 亦无效，E046）；`mkdir` 生成 `drwxrws--x` 则可写。
- **最小修改**：build-only `mktemp` 包装器（把 `mktemp -d` 换成 `mkdir`），仅通过 PATH 前置作用于构建子进程
  （accel-config/4.1.9 先例；不写系统目录、不落地提交）。

### 5.5 上游测试链接错误：`aws-lc-sys` 未定义 AES/BN 符号

- **现象**：dev-dep 链 `ureq → rustls → aws-lc-rs → aws-lc-sys` 链接报大量
  `undefined symbol: aws_lc_0_40_0_ChaCha20_ctr32_neon / aes_hw_encrypt / bignum_copy_row_from_table ...`。
- **根因**（知识库 E385）：`aws-lc-sys` 的 CMake 子构建使用 SDK 的 `ohos.toolchain.cmake`，其
  `CMAKE_RANLIB` 指向本 SDK **不存在**的 `native/llvm/bin/llvm-ranlib`（仅有 `llvm-ar`），静态归档
  未建索引 → 最终链接缺符号。
- **最小修改**：生成只执行 `llvm-ar s` 的 `llvm-ranlib` 包装器 + 薄 CMake toolchain overlay
  （先 `include` 官方 `ohos.toolchain.cmake`，再 FORCE 覆盖 `CMAKE_RANLIB`/`CMAKE_C_COMPILER_RANLIB`/
  `CMAKE_ASM_COMPILER_RANLIB`），经 `AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos`
  注入（stalwart/1.0.5 先例）。

### 5.6 源码下载（本地环境）

github.com 本机直连超时；本地核验用 `codeload.github.com`（GitHub 官方归档后端）预置到 conan
`core.sources:download_cache`（按 sha256 命名），配方 conandata 仍保留官方 URL（R39）。CI 侧按其既有
下载通道获取同一 tarball。

## 6. 上游测试

命令（与上游 `make test-ci` = `cargo nextest run --profile ci` 等价口径，本机用 `cargo test`）：

```
cargo test --release --locked --target aarch64-unknown-linux-ohos --lib --test lib --no-fail-fast -- <skips>
```

| 目标 | 通过 | 失败 | 忽略 | 过滤 |
|------|------|------|------|------|
| `--lib`（src 单元） | 6353 | 0 | 2 | 24 |
| `--test lib`（tests/ 集成） | 5170 | 0 | 0 | 126 |
| **合计** | **11523** | **0** | **2** | **150** |

**全量执行（不做任何过滤）实测**：`--lib` 6374 通过 / 3 失败；`--test lib` 5265 通过 / 28 失败；
`--bin rumdl`（139 用例）SIGSEGV。失败分类与依据见 `reports/test-report.md`：

1. **perf/memory/benchmark/complexity/scaling**（15 项）：计时敏感；**上游自身 CI 即过滤**
   （`nextest.toml` `[profile.ci] default-filter`），故一致排除。
2. **chmod/权限类**（5 项）：HMDFS 忽略 chmod/set_permissions（E046），断言"不可读文件应报错"
   "fix 必须保留 0600"等在本平台不成立。鸿蒙平台固有，非代码缺陷。
3. **CWD 污染类**（12 项）：部分用例 `set_current_dir` 到临时目录后删除，污染同进程其他用例的 CWD
   （`Failed to get current dir: NotFound` / `Failed to read README.md`）。**隔离运行全部通过**；
   上游 CI 用 **cargo-nextest（每用例独立进程）** 因而全绿——本机 rust-toolchain 包不含 nextest，
   故按名排除（已在单测隔离运行中确认通过）。
4. **`--bin rumdl` 测试二进制 SIGSEGV**：该二进制是唯一把 jemalloc 作为 `#[global_allocator]` 的
   测试二进制，在 libtest 下**对任意用例**（含纯计算用例）崩溃；已排除 initial-exec TLS
   （`CARGO_FEATURE_DISABLE_INITIAL_EXEC_TLS=1`）、jemalloc arena（`MALLOC_CONF=narenas:1`）、
   线程栈（`RUST_MIN_STACK`）等变量，仍复现。**交付二进制本身正常**（`--version/--help/check/fmt`、
   40 文件 rayon 并行检查均正确）。属平台/测试框架限制。

鸿蒙特有测试：`test_package/test_rumdl.py` 4 项断言（AArch64 ELF / musl loader / OHOS code signature /
产物完整性），随 `conan create` 自动执行。

## 7. ELF 签名（必须）

OHOS 拒绝执行未签名 ELF。`package()` 前对 `bin/rumdl` 用
`binary-sign-tool sign -selfSign 1` 自签，`test_package` 以 `.codesign` 段存在作为一项鸿蒙特有断言。

## 8. 交付物

| 文件 | 说明 |
|------|------|
| `bin/rumdl` | 命令行工具（约 13.8 MB，AArch64/musl/已签名） |

## 9. 知识引用

- E046 —— HMDFS/SELinux 下 chmod 不生效
- E011 / E112 —— HMDFS 上 autoconf `config.status` 的 `mktemp -d`(umask 077) 目录不可写
- E385 —— Cargo 原生 CMake 子构建补全 OHOS SDK 缺失的 `llvm-ranlib`（aws-lc-sys AES/BN 未定义符号）
- E180 —— Rust 在 OHOS 上原生编译（宿主三元组即 `aarch64-unknown-linux-ohos`）
- E340 —— Conan 打包 cargo 项目
- E002 —— OHOS `/tmp` 只读（TMPDIR 需改可写）
---

**编译结束**: 2026-10-01 16:52
**最终状态**: built
