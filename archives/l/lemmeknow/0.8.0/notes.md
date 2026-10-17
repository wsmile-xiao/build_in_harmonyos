# lemmeknow 0.8.0 适配笔记

## 软件信息
- 上游仓库: https://github.com/swanandx/lemmeknow（MIT，最后发布 2023-05-20，0.8.0 为最终版本）
- 语言: Rust（edition 2021，纯 Rust，Cargo.lock 123 项全为纯 Rust 依赖，无 C/C++）
- 构建系统: cargo（单 crate：lib + bin，default feature `cli` = clap4 + comfy-table）
- 编译环境: HarmonyOS PC（aarch64），rustc/cargo 1.97.1（rust-toolchain/1.97.1 包，host target = aarch64-unknown-linux-ohos），OHOS SDK clang
- 编译日期: 2026-09-25

## 源码与版本映射
- 官方归档二选一：crates.io .crate（含 Cargo.lock）与 GitHub tag `v0.8.0` tarball（无 lock）
- 本包选用 crates.io 归档：`https://static.crates.io/crates/lemmeknow/lemmeknow-0.8.0.crate`
- SHA256 = `6a84dc3c9c3aba3b43b2bccec7ff9ca15ee94e6644eac129fef1ffd13d9e4733`（与 crates.io API checksum 一致，设备实测一致）
- 内含 Cargo.lock → `cargo build/test --release --locked` 可复现构建

## 上游测试用例申报（R51 三步法）

### 1. 上游测试清点（静态统计）

| 测试类型 | 用例数 | 来源 |
|----------|--------|------|
| CLI 集成测试（assert_cmd） | 4 | tests/cli.rs |
| 识别器库级测试 | 4 | tests/identifier_check.rs |
| 正则规则校验 | 1 | tests/validate_regexes.rs |
| 单元测试 | 1 | src/lib.rs（it_works） |
| **合计** | **10** | 全部离线，无环境依赖 |

### 2. 上游测试实际运行（本机 = HarmonyOS PC）

- 运行方式：`cargo test --release --locked --tests --target aarch64-unknown-linux-ohos`
  （host = target，测试二进制真机直接执行；由配方 build() 集成执行）

**结果：10 通过 / 0 失败 / 0 忽略（通过率 100%）**

- doc-test 说明：`cargo test` 默认还会跑 2 个 rust doc-example（src/lib.rs
  模块文档），但 rust-toolchain/1.97.1 基础设施包不含 rustdoc 二进制
  （实测 bin/ 仅有 cargo/rustc/clippy/rustfmt 等），doctest 无法执行；
  且该 2 个 doc-example 与 tests/identifier_check.rs 的 to_json 序列化
  覆盖面重复。故以 `--tests` 显式覆盖全部 10 个测试目标并排除 doctest。

### 3. 失败用例逐项技术原因

无失败用例。

## 编译过程与平台适配

配方以 below/0.11.0（CI PASSED 的 Rust 移植先例）为模板，去除 libelf/zlib 依赖、
libbpf 补丁与依赖路径注入（lemmeknow 无 C 依赖），保留 Rust 工具链接入全套处理：

| # | 平台问题 | 处理（配方内自动化） |
|---|----------|----------------------|
| 1 | 设备无 cargo/rustc | tool_requires `rust-toolchain/1.97.1`（宿主+目标均为 aarch64-unknown-linux-ohos） |
| 2 | rust-lang dist 二进制无 code signature，OHOS 拒绝 execve（EACCES，E318 同类） | `_prepare_signed_toolchain()`：cargo/rustc/librustc_driver-*.so 复制进 build_folder 用 `binary-sign-tool -selfSign 1` 自签名，rustlib 等只读负载软链；marker 幂等 |
| 3 | cargo 动态链接 OpenSSL/zlib，OHOS loader 忽略 DT_RUNPATH，系统 OpenSSL 3.0 缺 SSL_get0_group_name | `_prepare_runtime_libs()`：harmonybrew `openssl@3-3.6.4` + `zlib-ng-compat-2.3.3_1` bottle（sha256 校验），lib 目录前置进 LD_LIBRARY_PATH |
| 4 | 设备无默认 CA store，cargo 拉 sparse 索引报 CERTIFICATE_VERIFY_FAILED | `_ca_bundle()` 探测系统 cacert.pem → `SSL_CERT_FILE`/`CURL_CA_BUNDLE` + `$CARGO_HOME/config.toml` cainfo；crates 索引走 rsproxy.cn |
| 5 | rustup 无法识别 HarmonyOS 宿主（E105/E154） | 全程禁止 rustup 引导 |
| 6 | OHOS /tmp 只读（E002）；cargo 临时文件与 tests/cli.rs 的 assert_fs 临时样本需要可写 TMPDIR | `_ensure_writable_tmpdir()`：已有可写 TMPDIR 则不动，否则落 `~/tmp` |
| 7 | OHOS 无 cc 符号链接 | `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER` = OHOS SDK `aarch64-unknown-linux-ohos-clang` |

## 源码修改

无（零补丁：上游代码未做任何修改，构建/测试全部通过配方环境处理）。

## 依赖版本
- rustc/cargo 1.97.1（rust-toolchain/1.97.1，aarch64-unknown-linux-ohos）
- OHOS SDK clang（aarch64-unknown-linux-ohos-clang，链接器）

## 验证结果

```bash
cargo test --release --locked --target aarch64-unknown-linux-ohos
# 10 passed; 0 failed; 0 ignored → 通过率 100%
```

### 消费者功能测试（test_package/test_lemmeknow.py）

test_package 断言 8 项（全部通过）：
- 鸿蒙特有 4 项：B1 ELF machine=AArch64(183) / B2 PT_INTERP=ld-musl-aarch64.so.1 / B3 含 OHOS code signature / B4 非空可执行
- 消费者 4 项：A1 `--help` 退出码 0 / A2 help 输出含 usage / A3 `--version` 输出 0.8.0 / A4 `lemmeknow 127.0.0.1` 识别出 Internet Protocol

### 权威 CI

见 progress.json `authoritative_ci` 字段与 CI 日志（`ci/conan/build_and_test.sh`，
profile `ci/conan/profiles/ohos-aarch64`，日志 `.ci_logs/conan_build_lemmeknow_0.8.0.log`）。
