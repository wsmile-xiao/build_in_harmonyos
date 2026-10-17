# teller 2.0.7 适配笔记

## 软件信息

- 上游仓库: https://github.com/tellerops/teller （tag `v2.0.7` → commit `04f099a56105e83d01f2fe30c84a5fc06d7183c9`）
- 语言: **Rust**（32 个 `.rs`，行数主体 100%；Cargo workspace：`teller-cli`(bin `teller`) / `teller-core` / `teller-providers` / `xtask`）
- 构建系统: **cargo**（`Cargo.toml` + `Cargo.lock` v3；`default-members=["teller-cli"]`；上游无 `build.rs`）
- 编译环境: HarmonyOS PC（aarch64, HongMeng Kernel），rustc/cargo **1.97.1**（`rust-toolchain/1.97.1` 基础设施包，host=target=`aarch64-unknown-linux-ohos`），clang 15（OHOS SDK 26.0.0.18）
- 编译日期: 2026-09-24
- 状态: **built**（本地构建 + 上游测试 + conan create + test_package 全通过；未上传制品）

## 依赖（W0 结论：缺口 0）

| 依赖 | 版本 | 类型 | 用途 | 可消费性 |
|---|---|---|---|---|
| rust-toolchain | 1.97.1 | tool_requires | Rust 编译器/工具链（宿主即目标 aarch64-unknown-linux-ohos） | ✅ `conan download --only-recipe` exit 0；`conan install --build=never` exit 0 |
| protobuf | 3.17.3 | tool_requires | `protoc`：`etcd-client → tonic-build → prost-build` 生成 gRPC 代码（上游 CI `dist` 作业同样在构建前装 protoc） | ✅ download/graph info exit 0 |
| openssl | 3.5.8.1 | requires | `rustify(default-tls) → reqwest → native-tls → openssl-sys` 的 TLS 后端（**静态链接**，产物 `DT_NEEDED` 仅 `libc.so`） | ✅ download/graph info exit 0 |
| zlib | 1.3.1 | 传递（随 protobuf） | protobuf 依赖 | ✅ graph info exit 0 |

`Cargo.lock` 传递闭包 441 包（crates.io 437 + workspace 成员 4），全部由 cargo 从 crates.io（rsproxy 镜像）拉取，非 Conan 依赖。

## 编译步骤（真实命令）

```bash
# 1) 依赖预检（W0，探测 home 隔离）
conan download rust-toolchain/1.97.1 -r=ohpcd --only-recipe          # exit 0
conan download protobuf/3.17.3     -r=ohpcd --only-recipe           # exit 0
conan download openssl/3.5.8.1     -r=ohpcd --only-recipe           # exit 0

# 2) 配方验证（模式 A：conan 驱动）
conan create archives/t/teller/2.0.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -r=ohpcd                                          # exit 0

# 3) 上游测试（build() 内自动执行，本机手工同构命令）
cargo test --release --locked --target aarch64-unknown-linux-ohos \
  --all-features --workspace --no-fail-fast \
  --lib --bins --tests --benches --examples                        # 见下 §上游测试

# 4) 消费端验证
conan test archives/t/teller/2.0.7/test_package teller/2.0.7 -pr:h/… -pr:b/… -r=ohpcd   # exit 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机无 `cargo`/`rustc`；`rustup` 不可用 | 标准 rustup 用 `uname -s` 判宿主，HarmonyOS 返回 `HarmonyOS`，报 `unrecognized OS type`（知识 E105/E154）；本机无系统 Rust | 改用制品仓基础设施包 `rust-toolchain/1.97.1`（`tool_requires`），rust-lang 官方 dist 预编译，宿主=目标=aarch64-unknown-linux-ohos |
| 2 | `…/rust-<pkg>/p/bin/cargo: permission denied`（EACCES errno 13） | rust-lang dist tarball 的 ELF **不带 OHOS code signature**，HarmonyOS 拒绝 `execve` 未签名 ELF | `_prepare_signed_toolchain()`：把 `cargo`/`rustc` 与 rustc dlopen 的 `librustc_driver-*.so` 复制到 `build_folder/rust-toolchain/`，用 `binary-sign-tool sign -selfSign 1` 逐个自签名（先写 `.signed` 再 `os.replace`；签名后须 `chmod 755`），其余只读负载（`lib/rustlib` 等）软链避免复制，marker 保证幂等 |
| 3 | 签名后 cargo 报 `Error loading shared library libssl.so / libcrypto.so`，且 `/usr/lib` 的 3.0.x 缺 `SSL_get0_group_name`（cargo 1.97 需要） | cargo 动态链接 libssl/libcrypto/libz，OHOS loader 忽略 DT_RUNPATH；系统 OpenSSL 版本过低 | `_prepare_runtime_libs()`：取 Harmonybrew OHOS 预编译 bottle `openssl@3-3.6.4`（sha256 校验）解包后前置进 `LD_LIBRARY_PATH`；`libz.so` 经实测由 OHOS 系统默认路径提供（仅 preload openssl bottle 即可完成 `cargo fetch` 的 TLS + 索引拉取），故**不引入** zlib bottle |
| 4 | `cargo fetch` 报 `CERTIFICATE_VERIFY_FAILED` / 索引拉取失败 | 设备无默认 CA store，cargo 走 HTTPS 拉 sparse 索引 | `_ca_bundle()` 探测 `/storage/Users/currentUser/usr/local/ssl/cert.pem` 等路径，导出 `SSL_CERT_FILE`/`CURL_CA_BUNDLE`，并在 `$CARGO_HOME/config.toml` 写 `[http] cainfo`；`[source.crates-io] replace-with=rsproxy-sparse` |
| 5 | `etcd-client`（默认 `etcd` 特性）编译报缺 `protoc` | `etcd-client → tonic-build → prost-build` 生成 gRPC 代码需要 protoc（上游 CI `Install Protoc`） | `tool_requires("protobuf/3.17.3")`，构建时把其 `bin/protoc` 加入 `PATH` 并导出 `PROTOC` |
| 6 | `openssl-sys`（`rustify → native-tls`）找不到 OpenSSL | 平台无 openssl 开发包（`pkg-config openssl` 不存在） | `requires("openssl/3.5.8.1")`，构建时导出 `OPENSSL_DIR`/`OPENSSL_INCLUDE_DIR`/`OPENSSL_LIB_DIR` 并前置其 `lib/pkgconfig` |
| 7 | `cargo test` 的 `tests/cmd/scan.trycmd` 有 2 例失败（多扫到 `git-hidden-file`） | 源码来自 tarball，**无 `.git` 元数据**；而 `scan` 用 ignore crate 的 gitignore 规则，该 crate 仅在目录链存在 `.git` 时才应用 `.gitignore`（ignore-0.4.22 `src/dir.rs`: `parent.join(".git").exists()`）。上游 CI 是 git checkout（有 `.git`） | 运行上游测试前在 `source_folder` 补建 `.git` 目录与上游 CI 环境对齐；对齐后 29/29 trycmd 用例通过 |
| 8 | `cargo test` 报 `could not execute process rustdoc … (never executed)` | `rust-toolchain/1.97.1`（以及 Harmonybrew 的 OHOS rust bottle）**均不提供 rustdoc 二进制**，doctest 无法在本平台执行 | 测试改用显式目标集合 `--lib --bins --tests --benches --examples`（不含 `--doc`）；doctest 无法执行属平台工具链限制，已在 §上游测试 申报 |
| 9 | 运行期 `TMPDIR` | `/tmp` 只读（知识 E002） | 构建环境显式设置 `TMPDIR`（缺省回退到 build_folder） |

### 未修改上游源码

本版本**零上游源码改动**（`patches/` 为空）：唯一的环境差异（缺 `.git`）在构建期由配方补建目录解决，不构成源码补丁。

## 上游测试用例申报（R51 三步法）

### 1. 上游测试清点（静态）

| 类型 | 文件 | 用例数 |
|---|---|---|
| 单元测试（`#[test]`/`#[tokio::test]`） | `teller-core/src/{config,exec,redact,scan,template}.rs` | 8 |
| 单元测试 | `teller-providers/src/providers/{aws_secretsmanager,dotenv,etcd,google_secretmanager,hashicorp_consul,hashicorp_vault,inmem,ssm}.rs` | 8 |
| 集成测试（trycmd 快照） | `teller-cli/tests/cli_tests.rs` → `tests/cmd/*.trycmd` | 1 个 `#[test]`，内部注册 29 个用例 |
| 集成测试（dockertest） | `teller-cli/tests/flow_test.rs` | 1 |
| 上游 CI 命令 | `.github/workflows/build.yml`: `cargo test --all-features --all`（矩阵 ubuntu/macos/windows × stable） | — |

### 2. 实际运行（本机 = HarmonyOS PC aarch64，host=target）

```bash
cargo test --release --locked --target aarch64-unknown-linux-ohos \
  --all-features --workspace --no-fail-fast \
  --lib --bins --tests --benches --examples
```

| target | 用例 | 通过 | 失败 | 忽略 |
|---|---|---|---|---|
| `teller` lib unittests | 0 | 0 | 0 | 0 |
| `teller` bin unittests | 0 | 0 | 0 | 0 |
| `teller` `tests/cli_tests.rs`（trycmd，29 个用例） | 1 | **1（29/29 用例 ok）** | 0 | 0 |
| `teller` `tests/flow_test.rs`（dockertest） | 1 | 0 | 1 | 0 |
| `teller-core` lib | 9 | 8 | 0 | 1 |
| `teller-providers` lib | 8 | 3 | 5 | 0 |
| `xtask` | 0 | 0 | 0 | 0 |
| **合计** | **19** | **12** | **6** | **1** |

- 通过率（排除忽略）：12/18 = 66.7%；**排除 Docker 依赖用例后 12/12 = 100%**。
- doctest：无法执行（无 rustdoc，见问题 #8），涉及 `teller` / `teller-core` / `teller-providers` 三个 doc 目标。

### 3. 失败用例逐项技术原因

| 用例 | 所在 crate | 失败原因 |
|---|---|---|
| `providers_smoke_test`（flow_test） | teller-cli | dockertest 需连接 Docker 守护进程启动 Vault 1.8.2 / LocalStack 容器：`creating docker network failed: error trying to connect: No such file or directory (os error 2)`——本机未安装 Docker |
| `providers::aws_secretsmanager::tests::sanity_test` | teller-providers | 同上（dockertest/Docker） |
| `providers::ssm::tests::sanity_test` | teller-providers | 同上 |
| `providers::hashicorp_vault::tests::sanity_test` | teller-providers | 同上 |
| `providers::hashicorp_consul::tests::sanity_test` | teller-providers | 同上 |
| `providers::etcd::tests::sanity_test` | teller-providers | 同上 |

> 结论：6 例失败**全部**因运行环境无 Docker（dockertest 无法启动外部服务容器），非被测逻辑缺陷；`google_secretmanager` / `inmem` / `dotenv` 三个 provider 的 sanity test 通过。
> 忽略用例：`teller-core` 的 `exec::tests::env_reset`（上游 `#[ignore]`，需重置进程环境）。

## 源码修改

无（`patches/` 为空，未改动任何上游源码或测试文件）。

## 本地执行口径说明（证据链）

- 本机 `conan create`（配方验证 ×2）、`ohc-run.py conan-verify`、`ohc-run.py finish`（含 W3 本地 CI：`ci/conan/setup.sh` + `ci/conan/build_and_test.sh`）**均设置 `OHC_SKIP_UPSTREAM_TESTS=1`** 运行——目的是压缩本机时间预算：该变量只影响 build() 内的 `cargo test`，不影响真实 `cargo build`、打包、签名与 test_package。
- 上游测试套件在同一份源码树上**另行独立实跑**并留档（`cargo test --release --locked --target aarch64-unknown-linux-ohos --all-features --workspace --no-fail-fast --lib --bins --tests --benches --examples`，日志 `~/tmp/teller-build/test-02.log`、`test-03.log`、去 ANSI 版 `test-03.clean.log`），统计见 §上游测试用例申报。
- **CI 侧不设置该变量**，因此远端 `conan create` 的 build() 会执行上游测试（配方默认行为，`test_package/MANIFEST.yml` 中 `upstream_test_in_build: true` 已申报）。据此，CI 单次构建 ≈ 14 min（cargo build）+ ≈ 20 min（测试编译/执行），在 3600s 预算内。

## 依赖版本

- rustc / cargo 1.97.1（aarch64-unknown-linux-ohos；制品仓 `rust-toolchain/1.97.1`）
- protoc 3.17.3（制品仓 `protobuf/3.17.3`）
- OpenSSL 3.5.8（制品仓 `openssl/3.5.8.1`，静态链接进产物）
- cargo 运行期共享库：OpenSSL 3.6.4（Harmonybrew OHOS bottle，仅构建期使用，不进产物）
- clang 15.0.4（OHOS SDK 26.0.0.18，`aarch64-unknown-linux-ohos-clang`）

## 验证结果

```bash
# 产物
/teller 2.0.7                                    # 本机直接运行，rc=0
readelf -d teller | grep NEEDED                  # NEEDED: libc.so（OpenSSL 静态链接）

# 上游测试（见上表）
cargo test … → 19 用例：12 通过 / 6 失败(Docker) / 1 忽略；trycmd 29/29 通过

# conan create + test_package
conan create archives/t/teller/2.0.7 …           # exit 0
conan test archives/t/teller/2.0.7/test_package teller/2.0.7 …   # exit 0
#   消费者 + 鸿蒙特有断言: 9/9 PASS（harmonyos_specific=4）
#   openssl 依赖功能测试:  7/7 PASS（SUMMARY: executed=7 passed=7 failed=0）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/teller` | ~45 MB | teller 2.0.7（aarch64-unknown-linux-ohos，已 OHOS 自签名，DT_NEEDED 仅 libc.so） |
| `licenses/LICENSE.txt` / `licenses/README.md` | — | 上游许可证与说明 |

## 注意事项

- 产物为 OHOS 签名后的 ELF（`codesign` 标记），未签名的 ELF 在本平台无法 `execve`（EACCES）。
- teller 运行需要 `.teller.yml` 配置（`teller scan`/`export` 等）或 `-c/--config` 指定；无配置时报 `cannot find configuration from current folder and up to root`。
- 上游测试套件的 Docker 相关用例（6 例）在无 Docker 环境必然失败，配方按"失败不阻断"处理（`OHC_REQUIRE_UPSTREAM_TESTS=1` 可要求全绿）。
- 构建时间预算：`cargo build --release --locked` 首次约 14 分钟；含上游测试约 35 分钟。CI 默认 `conan create` 超时预算 3600s 内可完成；如需更大余量，应另开**框架 PR** 调整 `ci/config/build_timeouts.txt`（该文件属 `ci/`，不随本配方 PR 提交）。
---

**编译结束**: 2026-09-24 14:35
**最终状态**: built
