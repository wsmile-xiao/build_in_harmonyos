# rudof 0.3.6 适配笔记

## 软件信息
- 上游仓库: https://github.com/rudof-project/rudof（MIT OR Apache-2.0）
- 语言: Rust（cargo workspace，`edition 2024`；CLI crate = `rudof_cli`，产物二进制名 `rudof`）
- 构建系统: cargo（本包只发布 `rudof_cli` crate）
- 编译环境: HarmonyOS PC（aarch64），rustc/cargo 1.97.1（rust-toolchain/1.97.1 包，
  host target = aarch64-unknown-linux-ohos），OHOS SDK clang
- 编译日期: 2026-10-01

## 源码与版本映射
- 官方归档二选一：crates.io `.crate`（含发布时一致的 `Cargo.lock`）与 GitHub tag `0.3.6` tarball
- 本包选用 crates.io 归档：`https://static.crates.io/crates/rudof_cli/rudof_cli-0.3.6.crate`
- SHA256 = `537b1c355bb4d11a1063a69bcdd7c616ed9cc4a0c84d81b289fe586af2c0b948`
  （与 crates.io API checksum 一致，设备实测一致）
- 选 crates.io 而非 GitHub tag 的原因：
  1. GitHub tag `0.3.6` 的根 `Cargo.lock` 仍记录各成员为 `0.3.5`
     （`release.yml` 只 bump `Cargo.toml` 不动锁），`cargo --locked` 会失败；
  2. GitHub tag tarball 的 `shex_testsuite/shexTest` 与 `shacl/tests/data-shapes`
     是**未随归档附带的 git 子模块**，`cargo test --workspace` 无法完整运行。
  crates.io 的 `rudof_cli` 归档内含发布时一致的锁，`cargo --locked` 可复现构建。
- 版本锚点：crate 内 `.cargo_vcs_info.json` `git.sha1 = b038e283a4b30f8bf6df60955c38782416f2f308`
  （= GitHub tag `0.3.6`），`path_in_vcs = "rudof_cli"`。

## 上游测试用例申报（R51 三步法）

### 1. 上游测试清点（静态统计）

`rudof_cli` crate（crates.io 发布版）内的全部上游测试：

| 测试类型 | 用例数 | 来源 |
|----------|--------|------|
| 单元测试（backend 参数解析 / 后端策略） | 11 | src/cli/wrappers/backend.rs（`#[cfg(test)] mod tests`） |
| **合计** | **11** | 全部离线，无环境依赖 |

- 该 crate 不含 `tests/` 集成测试目录；`Cargo.toml` 无 `[dev-dependencies]`。
- 说明：上游仓库是 22 成员 workspace，`cargo test --workspace` 会额外跑其它成员
  （workpace 内共 723 个 `#[test]`）。但其中 `shex_testsuite`（依赖 git 子模块
  `shexTest`）、`shacl`（依赖子模块 `data-shapes`）等需要未随源码归档提供的外部数据；
  上游 CI 用 `--features qlever` 还会拉起 Docker（testcontainers/bollard）后端。
  本包发布对象 = `rudof_cli` crate，故如实运行该 crate 的全部上游测试。

### 2. 上游测试实际运行（本机 = HarmonyOS PC）

- 运行方式：`cargo test --release --locked --target aarch64-unknown-linux-ohos --tests`
  （host = target，测试二进制真机直接执行；由配方 build() 集成执行）

**结果：11 通过 / 0 失败 / 0 忽略（通过率 100%）**

```
running 11 tests
test cli::wrappers::backend::tests::display_round_trips ... ok
test cli::wrappers::backend::tests::parses_memory ... ok
test cli::wrappers::backend::tests::parses_endpoint_name ... ok
test cli::wrappers::backend::tests::parses_endpoint_url ... ok
test cli::wrappers::backend::tests::parses_qlever ... ok
test cli::wrappers::backend::tests::preserves_case_in_endpoint_value ... ok
test cli::wrappers::backend::tests::rejects_bare_endpoint ... ok
test cli::wrappers::backend::tests::rejects_unknown_value ... ok
test cli::wrappers::backend::tests::resolve_backend_defaults_to_memory_when_both_absent ... ok
test cli::wrappers::backend::tests::resolve_backend_prefers_endpoint_shortcut ... ok
test cli::wrappers::backend::tests::resolve_backend_uses_backend_when_endpoint_absent ... ok

test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```
（bin 目标 `src/main.rs`：`running 0 tests`，无 bin 级测试。）

- doc-test 说明：`cargo test` 默认还会跑 rust doc-example，但 rust-toolchain/1.97.1
  基础设施包不含 rustdoc 二进制（实测 bin/ 仅有 cargo/rustc/clippy/rustfmt 等），
  doctest 无法执行；故以 `--tests` 显式覆盖 lib + bin 测试目标。

### 3. 失败用例逐项技术原因

无失败用例。

## 编译过程与平台适配

配方以 lemmeknow/0.8.0、below/0.11.0（CI PASSED 的 Rust 移植先例）为模板，保留
Rust 工具链接入全套处理：

| # | 平台问题 | 处理（配方内自动化） |
|---|----------|----------------------|
| 1 | 设备无 cargo/rustc | tool_requires `rust-toolchain/1.97.1`（宿主+目标均为 aarch64-unknown-linux-ohos） |
| 2 | rust-lang dist 二进制无 code signature，OHOS 拒绝 execve（EACCES，E318 同类） | `_prepare_signed_toolchain()`：cargo/rustc/librustc_driver-*.so 复制进 build_folder 用 `binary-sign-tool -selfSign 1` 自签名，rustlib 等只读负载软链；marker 幂等 |
| 3 | cargo 动态链接 OpenSSL/zlib，OHOS loader 忽略 DT_RUNPATH，系统 OpenSSL 3.0 缺 SSL_get0_group_name | `_prepare_runtime_libs()`：harmonybrew `openssl@3-3.6.4_1` + `zlib-ng-compat-2.3.3_2` bottle（sha256 校验），lib 目录前置进 LD_LIBRARY_PATH |
| 4 | 设备无默认 CA store，cargo 拉 sparse 索引报 CERTIFICATE_VERIFY_FAILED | `_ca_bundle()` 探测系统 cacert.pem → `SSL_CERT_FILE`/`CURL_CA_BUNDLE` + `$CARGO_HOME/config.toml` cainfo；crates 索引走 rsproxy.cn |
| 5 | rustup 无法识别 HarmonyOS 宿主（E105/E154） | 全程禁止 rustup 引导 |
| 6 | OHOS /tmp 只读（E002） | `_ensure_writable_tmpdir()`：已有可写 TMPDIR 则不动，否则落 `~/tmp` |
| 7 | OHOS 无 cc 符号链接 | `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER` = OHOS SDK `aarch64-unknown-linux-ohos-clang` |
| 8 | 本机宿主安全策略禁止 python 进程创建符号链接（`os.symlink` 报 EACCES，HMDFS/SELinux 限制，见 SKILL §7） | `_link_or_copy()`：优先软链（CI 常规路径），失败回退为复制，保证两种环境均可构建 |

## 源码修改

无（零补丁：上游代码未做任何修改，构建/测试全部通过配方环境处理）。

## 依赖版本
- 构建工具链: rust-toolchain/1.97.1（rustc/cargo，aarch64-unknown-linux-ohos）
- 链接器: OHOS SDK clang（aarch64-unknown-linux-ohos-clang）
- Rust crate：29 条直接 + 517 条传递（CLI 闭包 518 包），全部 crates.io registry crate，
  由 cargo 从 rsproxy.cn 镜像拉取，无 C/C++ 目标依赖包

## 验证结果

```bash
cargo test --release --locked --target aarch64-unknown-linux-ohos --tests
# 11 passed; 0 failed; 0 ignored → 通过率 100%
```

### 消费者功能测试（test_package/test_rudof.py）

test_package 断言 8 项（全部通过）：
- 鸿蒙特有 4 项：B1 ELF machine=AArch64(183) / B2 PT_INTERP=ld-musl-aarch64.so.1 /
  B3 含 OHOS code signature / B4 非空可执行
- 消费者 4 项：A1 `--help` 退出码 0 / A2 help 列出子命令 / A3 `--version` 输出 `rudof 0.3.6` /
  A4 `rudof data sample.ttl` 真实加载并重新序列化 Turtle 图（输出含 `@prefix ex:`）

### conan-verify
`conan-verify rudof 0.3.6` → G0-G4 + L2/L4/L5 全 PASS，EXIT=0
（报告：`archives/r/rudof/0.3.6/reports/conan-verify-report.md`）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/rudof | ~44.6 MB | 已签名 OHOS aarch64 ELF（`rudof --version` → `rudof 0.3.6`） |

## 注意事项

- 本机（agent 环境）python 进程无法创建软链，`_link_or_copy()` 回退复制会导致单次
  conan create 额外复制 rust-toolchain sysroot（~889MB）；CI（Linux）走软链，无此开销。
- 若后续需运行 workspace 级测试套件，需额外获取 `shexTest` / `data-shapes` 子模块数据，
  并隔离 `qlever`（Docker）后端。
---

**编译结束**: 2026-10-01 14:47
**最终状态**: built
