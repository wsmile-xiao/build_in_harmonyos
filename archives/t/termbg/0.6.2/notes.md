# termbg 0.6.2 适配笔记（notes.md）

- 目标库：**termbg / 0.6.2**（Rust crate；cargo；产物 `bin/termbg`）
- 上游：<https://github.com/dalance/termbg>，tag `v0.6.2`
  = commit `c5b066a56bf3a20b4942768f5e0da8eb29292a5b`（crate 内 `.cargo_vcs_info.json`）
- 源码：crates.io 官方 crate `https://static.crates.io/crates/termbg/termbg-0.6.2.crate`
  sha256 `8bf44577a1adf3dfd7fec3b8763074467e27b2ad35ff9157bc3f0a51bb0a3dd4`（实测一致）
- 构建日期：2026-09-24｜状态：`built`
- **上游源码零改动**：`patches_applied: []`（无 patches/ 目录）

---

## 1. 源码与上游测试入口核验

| 项 | 命令 | 结果 | 退出码 |
|---|---|---|---|
| 源码格式 | `tar -tzf termbg-0.6.2.crate \| head` | 顶层 `termbg-0.6.2/`（`.cargo_vcs_info.json`、`Cargo.toml`、`src/`） | 0 |
| build.rs 存在性 | `find .work/crate-x/termbg-0.6.2 -name build.rs` | **无**（`Cargo.toml` `build = false`） | — |
| 构建系统 | 读 `Cargo.toml` | cargo，无 CMake/autotools/meson | — |
| 测试入口 | `ls tests/` | **无 tests/ 目录**（上游唯一测试入口是 `src/lib.rs` 的 `#[cfg(test)] mod tests`） | — |
| 测试清点 | `grep -c '#\[test\]' src/lib.rs` | **6**（`src/bin/termbg.rs` = 0） | 0 |
| 上游 CI 入口 | `.github/workflows/rust.yml` | `Build: cargo build --verbose` / `Run tests: cargo test --verbose` | 0 |

6 个用例（`src/lib.rs:811-878`）：

1. `tests::test_query_xterm_with_various_terminators`
2. `tests::test_query_xterm_timeout_no_response`
3. `tests::test_query_xterm_timeout_incomplete_response_1`
4. `tests::test_query_xterm_timeout_incomplete_response_2`
5. `tests::test_query_xterm_timeout_unterminated_response`
6. `tests::test_decode_x11_color`

> `--doc` 目标在本工具链上不可用：基础设施包 `rust-toolchain/1.97.1` 的 `bin/` 下
> **没有 rustdoc**（`ls bin/` 仅 cargo/cargo-clippy/cargo-fmt/clippy-driver/
> rust-analyzer/rust-gdb/rust-gdbgui/rust-lldb/rustc/rustfmt）。
> 实测 `cargo test ...`（不带 `--tests`）在 doc-test 阶段报
> `could not execute process 'rustdoc ...' (never executed) / No such file or directory`，
> 退出码 101。termbg 源码**无任何 doc 代码块**（`grep -c '```' src/lib.rs` = 0），
> 即 `--doc` 编译 0 个用例，故用 `--tests` 覆盖全部真实用例，无漏测。

## 2. OHOS 适配（构建环境层，源码零改动）

### 2.1 工具链：`tool_requires("rust-toolchain/1.97.1")`

不使用 rustup：标准 rustup 无法识别 HarmonyOS 宿主（`unrecognized OS type: HarmonyOS`，
知识 E105/E154）。该基础设施包已发布在 ohpcd 制品仓（`conan download
rust-toolchain/1.97.1 -r=ohpcd --only-recipe` → **exit 0**）。

**首个真实错误（本机）**：

```
zsh: permission denied: .../p/rust-1b22ad19431ff/p/bin/cargo
```

根因：rust-toolchain 包内是 rust-lang 官方 dist 预编译产物，**无 code signature**，
HarmonyOS 拒绝 execve 未签名 ELF（EACCES / errno 13）。

修复：把 `cargo`/`rustc`/`librustc_driver*.so` 复制到 build 目录并用
`binary-sign-tool -selfSign 1` 自签名；其余只读负载（`lib/rustlib`、`etc`、`libexec`、
`share`）用符号链接保持 `<root>/bin` + `<root>/lib/rustlib` 的 **sysroot 布局**
（rustc 以自身可执行文件路径上两级推导 sysroot）。见 `_prepare_signed_toolchain()`。

重新验证：

```
sign cargo rc=0 / sign rustc rc=0 / sign librustc_driver-75adf430b23f8c75.so rc=0
LD_LIBRARY_PATH=<...>/lib <root>/bin/rustc --version  →  rustc 1.97.1 (8bab26f4f 2026-07-14)   rc=0
```

CI 干净环境二进制可直接执行，配方用 `_cargo_works()`（实际执行 `cargo --version`）
探测，成功即直接用包内路径、**不做任何复制/签名** —— 探测失败才走签名副本。

### 2.2 cargo 运行库：系统 OpenSSL 缺符号（知识 E509）

**第二个真实错误**：

```
Error loading shared library libssl.so: (needed by .../bin/cargo)
Error relocating .../bin/cargo: OBJ_nid2sn: symbol not found
Error relocating .../bin/cargo: OSSL_PROVIDER_try_load: symbol not found
... (共 ~200 个 OPENSSL_3.0.0/3.5 符号)
cargo rc=127
```

根因：cargo 1.97 动态链接 `libssl.so`/`libcrypto.so`，需要 OpenSSL 3.5+
（`SSL_get0_group_name`、`OSSL_STORE_*`、`EVP_MAC_*` 等）；本机系统库过旧。
与知识条目 **E509** 的 error_signature 完全吻合。

修复：使用 Harmonybrew 的 OHOS 预编译 bottle（`rust_runtime` 声明在 conandata.yml，
sha256 固定），解包后把 `lib` 目录前置进 `LD_LIBRARY_PATH`：

```
openssl3: sha256 e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98  ✅ 匹配
zlib:     sha256 1c17a31f8104701bce6b471af8dbbd14bb67d16a504eec087018feb05493a430  ✅ 匹配
LLD_LIBRARY_PATH 前置后：cargo 1.97.1 (c980f4866 2026-06-30)  rc=0
```

下载失败只警告不中断（CI 镜像可能自带可用 OpenSSL）。

### 2.3 依赖源：rsproxy.cn 镜像 + CA bundle

crates.io 直连在设备上无可用 CA、速度差 → `$CARGO_HOME/config.toml` 写
`sparse+https://rsproxy.cn/index/` 替换源 + `[http] cainfo` + `[target.<triple>] linker`
（**不改源码树**；`$CARGO_HOME/config.toml` 是 cargo 实际读取位置）。

### 2.4 链接器

`CC/CXX = /data/service/hnp/bin/clang[++]`（来自 `tools.build:compiler_executables` 或
profile 默认），`RUSTFLAGS=-C linker=<clang>`，
`[target.aarch64-unknown-linux-ohos] linker = clang`。

### 2.5 第三个真实错误：conanbuild env 覆盖签名目录（librsvg round-39 同款）

首次 `conan create` 时 `cargo test` 通过但 `cargo build` 失败：

```
error: process didn't exit successfully: '.../rust-toolchain-signed/bin/rustc -vV' (exit status: 127)
Error loading shared library librustc_driver-75adf430b23f8c75.so: (needed by .../bin/rustc)
ERROR: termbg/0.6.2: Error in build() method ... ConanException: Error 101 while executing
```

根因：conan 的 `self.run()` **默认套用 conanbuild 环境**，把 `tool_requires
rust-toolchain/1.97.1` 注入的 `LD_LIBRARY_PATH=<pkg>/lib`（未签名副本所在目录）盖到
我们配置的签名目录之上，rustc 找不到 `librustc_driver*.so`。

修复：cargo 调用统一走 `subprocess.run(cmd, env=<显式 env 字典>)`
（`_run_cargo()`），彻底绕开 conanbuild env 注入；同时把命令与 `LD_LIBRARY_PATH`
写入 `cargo_build.log` / `upstream_cargo_test.log`。

## 3. 上游测试实际执行（R51 三步法第 2/3 步）

命令（配方 `build()` 内真实执行）：

```
cargo test --release --locked --tests --no-fail-fast --target aarch64-unknown-linux-ohos
```

原始输出（节选，日志见下）：

```
running 6 tests
test tests::test_decode_x11_color ... ok
test tests::test_query_xterm_timeout_incomplete_response_2 ... ok
test tests::test_query_xterm_timeout_incomplete_response_1 ... ok
test tests::test_query_xterm_timeout_unterminated_response ... ok
test tests::test_query_xterm_timeout_no_response ... ok
test tests::test_query_xterm_with_various_terminators ... ok

test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.01s
```

| 指标 | 数值 |
|---|---|
| 发现用例（静态清点） | **6** |
| 执行 | **6** |
| 通过 | **6** |
| 失败 | **0** |
| 忽略/跳过 | **0** |
| 通过率 | **100%** |
| 退出码 | **0** |

每个用例名称与状态（`res/upstream_test_result.json` 内 `cases` 字段，随包携带）：

| 用例 | 状态 |
|---|---|
| `tests::test_decode_x11_color` | ok |
| `tests::test_query_xterm_timeout_incomplete_response_1` | ok |
| `tests::test_query_xterm_timeout_incomplete_response_2` | ok |
| `tests::test_query_xterm_timeout_no_response` | ok |
| `tests::test_query_xterm_timeout_unterminated_response` | ok |
| `tests::test_query_xterm_with_various_terminators` | ok |

**无漏测**：`grep -c '#\[test\]'` 静态清点 6 == 实际执行 6；`tests/` 目录不存在；
`src/bin/termbg.rs` 无测试；`--doc` 无 doc 代码块（见 §1）。

测试日志路径（`conan create` 内产生的权威副本）：

```
<CONAN_HOME>/p/b/termb6de9034993b9f/b/build-release/upstream_cargo_test.log
<CONAN_HOME>/p/b/termb6de9034993b9f/b/build-release/cargo_build.log
```

标记（test_package 阶段重发，hmbs preflight 采集口径）：

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "cargo-test",
  "discovered": 6, "executed": 6, "passed": 6, "failed": 0, "skipped": 0, ...}
```

## 4. 真实构建与打包

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=missing
...
termbg/0.6.2: HMBS_UPSTREAM_TEST_RESULT={... "status": "passed" ...}
termbg/0.6.2: termbg built: <CONAN_HOME>/p/b/termb6de9034993b9f/b/build-release/target/aarch64-unknown-linux-ohos/release/termbg
termbg/0.6.2: Package '6b129b068851896169fae42d399fa922d239ce8a' created
======== Testing the package: Executing test ========
[ok] termbg test_package: all 12 assertions passed.
exit=0
```

产物 `bin/termbg`：ELF 64-bit LSB arm64，解释器 `/lib/ld-musl-aarch64.so.1`，
含 `.note.ohos.ident` 段，`-rwxrwx--- 903040 bytes`。

## 5. test_package（消费者 + 鸿蒙特有，12 条断言）

`test_package/test_termbg.py`（真实运行打包二进制，R34）：

- **消费者 8 条**：A1 `--version` 含 0.6.2；A2 默认运行退出码 0；
  A3 检测头部；A4 `Term :`；A5 `COLORFGBG=15;0` → `Color: R=0, G=0, B=0`；
  A6 同 → `Theme: Dark`；A7 `COLORFGBG=0;15` → `Theme: Light`；A8 非法参数退出码非 0。
- **鸿蒙特有 4 条**（≥1 满足）：B1 ELFCLASS64；B2 `e_machine=183` (EM_AARCH64)；
  B3 PT_INTERP = `/lib/ld-musl-aarch64.so.1`（OHOS musl，非 glibc）；
  B4 含 `.note.ohos.ident` 段。

`test_package/conanfile.py` 追加：从包内 `res/upstream_test_result.json` 重发
`HMBS_UPSTREAM_TEST_RESULT`（文件缺失或 status != passed → 显式失败，绝不静默通过）。

## 6. 知识库关联

| 知识 | 本次命中情况 |
|---|---|
| E509（OpenSSL 3.x 符号缺失） | **命中**：cargo rc=127 + `OBJ_nid2sn` 等符号 not found → 用 Harmonybrew OHOS bottle + LD_LIBRARY_PATH |
| E105 / E154（rustup 无法识别 HarmonyOS 宿主） | **命中**：改用 rust-toolchain/1.97.1 tool_requires，禁用 rustup |
| E186（OHOS musl ldso 忽略 RUNPATH） | 相关：cargo/rustc 的 `$ORIGIN/../lib` 不生效，故显式设 `LD_LIBRARY_PATH` |
| E358（旧 Cargo.lock 在 OHOS target_env 下不兼容） | **未命中/不适用**：本 crate 的 Cargo.lock（libc 0.2.158 / rustix 0.38.37 / mio 1.0.2 组合）在 rustc 1.97.1 + `target_env=ohos` 下**直接编译通过**，无需锁图迁移 |
| librsvg round-39 / below（conanbuild env 覆盖签名工具链） | **命中**：`self.run()` 注入的 tool_requires `LD_LIBRARY_PATH` 覆盖签名目录 → 改用 subprocess 显式 env |

## 7. 复现命令

```bash
export CONAN_HOME=<隔离 CONAN_HOME>
conan remote add ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
conan create archives/t/termbg/0.6.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```
---

**编译结束**: 2026-09-24 14:02
**最终状态**: built
