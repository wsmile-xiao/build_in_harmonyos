# 测试报告 — teller 2.0.7

> **项目**: teller 2.0.7（Rust/Cargo workspace，bin `teller`）
> **测试日期**: 2026-09-24
> **测试环境**: HarmonyOS PC aarch64（HongMeng Kernel），host=target=`aarch64-unknown-linux-ohos`，rustc/cargo 1.97.1，clang 15（OHOS SDK 26.0.0.18）
> **测试类型**: 官方测试套件（`cargo test`）+ conan test_package（消费者/鸿蒙特有/依赖功能）

---

## 一、测试摘要

### 1.1 上游测试套件（cargo test）

命令：

```bash
cargo test --release --locked --target aarch64-unknown-linux-ohos \
  --all-features --workspace --no-fail-fast \
  --lib --bins --tests --benches --examples
```

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总用例数（测试函数） | 19 | 100% |
| 通过 (PASS) | 12 | 63.2% |
| 失败 (FAIL) | 6 | 31.6% |
| 忽略 (IGNORED) | 1 | 5.3% |
| 其中 Docker 环境依赖导致失败 | 6 | — |

按 target 明细：

| target | 用例 | 通过 | 失败 | 忽略 |
|---|---|---|---|---|
| `teller` lib unittests | 0 | 0 | 0 | 0 |
| `teller` bin unittests | 0 | 0 | 0 | 0 |
| `teller` `tests/cli_tests.rs`（trycmd） | 1（内含 29 个快照用例） | **1（29/29 用例 ok）** | 0 | 0 |
| `teller` `tests/flow_test.rs`（dockertest） | 1 | 0 | 1 | 0 |
| `teller-core` lib | 9 | 8 | 0 | 1 |
| `teller-providers` lib | 8 | 3 | 5 | 0 |
| `xtask` | 0 | 0 | 0 | 0 |

**核心功能通过率**: ✅ **排除 Docker 依赖用例后 12/12 = 100%**（trycmd 端到端 CLI 29/29 全通过）

### 1.2 conan test_package（消费者验证）

| 层次 | 断言数 | 通过 | 失败 |
|---|---|---|---|
| 消费者冒烟 + 端到端（`--version` / `--help` / `export json` / `scan`） | 5 | 5 | 0 |
| 鸿蒙特有（ELF AArch64 / musl loader / OHOS code signature / 产物完整性） | 4 | 4 | 0 |
| 依赖功能测试（OpenSSL：version/SHA256/EVP/RAND/BN/AES-CBC 往返） | 7 | 7 | 0 |
| **合计** | **16** | **16** | **0** |

### 1.3 doctest

无法执行：`rust-toolchain/1.97.1` 与 Harmonybrew OHOS rust bottle 均不提供 `rustdoc` 二进制（`could not execute process rustdoc … (never executed)`）。涉及 `teller` / `teller-core` / `teller-providers` 三个 doc 目标，属**平台工具链限制**。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**（可运行用例 100%；trycmd 端到端 29/29；conan test_package 16/16）

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 运行环境无 Docker，dockertest 无法启动 Vault/LocalStack | 6 个用例（flow_test + 5 个 provider sanity test） | 🟡 环境限制 |
| OHOS Rust 发行版不含 rustdoc | 3 个 doc 测试目标 | 🟡 环境限制 |
| `teller-core` `exec::tests::env_reset` 上游标记 `#[ignore]` | 1 个用例 | 🟢 上游设计 |

### 2.3 可用功能清单

```
✅ CLI 基础: --version / --help / 子命令（run scan export redact template env show sh new put delete copy）
✅ trycmd 端到端 29 例: scan/export(txt,yaml,json,env,csv)/redact/new/put/delete/copy/run/template
✅ 配置与模板: config 加载、tera 模板渲染、config 模板化（teller-core）
✅ 扫描/脱敏: scan（位置/宽字符）、redact（none/some）、exec（run_echo）
✅ provider: dotenv / inmem / google_secretmanager 的 sanity test
✅ 依赖 OpenSSL 在 HarmonyOS 上的真实可用性（静态链接，消费端 C 程序实跑 7/7）
```

---

## 三、失败用例逐项技术原因（R51 第 3 步）

| 用例 | 所在 crate | 失败原因 |
|------|-----------|---------|
| `providers_smoke_test`（tests/flow_test.rs） | teller-cli | dockertest 需 Docker：`creating docker network failed: error trying to connect: No such file or directory (os error 2)`；本机未安装 Docker |
| `providers::aws_secretsmanager::tests::sanity_test` | teller-providers | 同上（dockertest/LocalStack） |
| `providers::ssm::tests::sanity_test` | teller-providers | 同上（dockertest/LocalStack） |
| `providers::hashicorp_vault::tests::sanity_test` | teller-providers | 同上（dockertest/Vault 1.8.2） |
| `providers::hashicorp_consul::tests::sanity_test` | teller-providers | 同上（dockertest/Consul） |
| `providers::etcd::tests::sanity_test` | teller-providers | 同上（dockertest/etcd） |

**忽略用例**：`teller-core` `exec::tests::env_reset`（上游 `#[ignore]`）。

> 判定：失败用例**全部**因缺少 Docker 运行环境（属"运行环境限制"，可换到有 Docker 的环境复跑），无一是被测逻辑缺陷或平台适配缺陷。上游测试用例**未被修改**（零补丁）。

---

## 四、修复与重新验证

| 问题 | 修复 | 重新验证 |
|---|---|---|
| trycmd `scan.trycmd` 2 例失败（多扫到 `git-hidden-file`） | 运行测试前在源码目录补建 `.git`（ignore crate 的 gitignore 语义要求存在 `.git`；上游 CI 为 git checkout） | 重跑 `cargo test --test cli_tests` → **1 passed（29/29 用例 ok）** |
| `test_package` A4/A5 失败（`export json`/`scan` 报 `cannot find configuration`） | 测试内补写 `.teller.yml`（dotenv provider 声明），与上游 fixture 一致 | `conan test` → **9/9 PASS** |
| 依赖测试断言 7 期望密文长度错误（写成明文+16） | 改为 PKCS#7 填充块长度 `(len/16+1)*16` | `conan test` → **7/7 PASS** |

---

## 五、测试命令与日志路径

| 测试 | 命令 | 退出码 | 日志 |
|---|---|---|---|
| 依赖预检（W0） | `conan download rust-toolchain/1.97.1 -r=ohpcd --only-recipe` | 0 | `logs/`（见工作站探测日志） |
| 真实构建（Step 2） | `cargo build --release --locked --target aarch64-unknown-linux-ohos` | 0 | `~/tmp/teller-build/build-01.log`（Finished in 14m06s） |
| 上游测试（Step 2） | `cargo test --release --locked --target … --all-features --workspace --no-fail-fast --lib --bins --tests --benches --examples` | 101（存在环境限制失败） | `~/tmp/teller-build/test-02.log`、`test-03.log`（去 ANSI：`test-03.clean.log`） |
| 配方构建（W3） | `conan create archives/t/teller/2.0.7 -pr:h/-pr:b=… --build=missing -r=ohpcd` | 0 | `reports/conan-create.log` |
| 消费端验证 | `conan test archives/t/teller/2.0.7/test_package teller/2.0.7 -pr:h/-pr:b=… -r=ohpcd` | 0 | `~/tmp/teller-build/conan-test-03.log` |
