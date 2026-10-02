# weggli 0.2.4 适配笔记（HarmonyOS PC / aarch64-unknown-linux-ohos）

- 上游：https://github.com/weggli-rs/weggli （原 googleprojectzero/weggli → google/weggli）
- 版本：0.2.4（tag `v0.2.4` = commit `ad8d424e0da5b65f72ce69a884f1cd95f596d85f`）
- 源码：`https://github.com/weggli-rs/weggli/archive/refs/tags/v0.2.4.tar.gz`
  sha256 `12fde9a0dca2852d5f819eeb9de85c4d11c5c384822f93ac66b2b7b166c3af78`（58 条目）
- 语言（R47）：`rust`（manifest `Cargo.toml`，13 个 `.rs` 主体源文件，占比 81%；crates.io 115 个包）
- 构建系统：`cargo`（`Cargo.toml` + `Cargo.lock`；`build.rs` 经 `cc` 编译树内 vendored C/C++ 语法解析器）
- 目标：`aarch64-unknown-linux-ohos`（OHOS aarch64 / armv8，clang 15，libc++，Release）
- 状态：built（conan create rc=0；上游 56 + Python 绑定 4 = 60/60 通过；尚未上传制品仓）

## 编译步骤

```bash
# 1) 源码与 sha256 核验（官方源，实测与 dep-analysis 一致）
sha256sum weggli-0.2.4.tar.gz   # 12fde9a0…af78
tar tzf weggli-0.2.4.tar.gz | wc -l   # 58

# 2) 配方构建（Rust 工具链来自制品仓基础设施包 rust-toolchain/1.97.1）
conan create archives/w/weggli/0.2.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → cargo build --release --locked --target aarch64-unknown-linux-ohos
# → cargo test  --release --locked --target aarch64-unknown-linux-ohos --lib --bins --tests
```

真实命令、原始输出、退出码与日志路径：见 `reports/adaptation-report.md`（每一步含日志文件与 rc）。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案（最小修改） |
|---|----------------------|------|----------------------|
| 1 | `error: could not compile libc` — 750 处 `cannot find type \`__u64\` in the crate root`（libc-0.2.112/src/unix/linux_like/linux/non_exhaustive.rs） | `rustc --print cfg --target aarch64-unknown-linux-ohos` 给出 `target_os="linux"` + `target_env="ohos"`；Cargo.lock 锁定的 libc 0.2.112（2022-01）早于 libc 对 `target_env="ohos"` 的处理（首个支持版本 0.2.140），其 linux/gnu、linux/musl 分支都不匹配 ohos → `::__u64` 等类型未定义 | `cargo update -p libc --precise 0.2.155`（nix 0.28 的约束下限；0.2.140 起支持 ohos）。见 `patches/0001-Cargo.lock.patch` |
| 2 | `error[E0004]: non-exhaustive patterns: signal::SigevNotify::SigevThreadId { .. } not covered`（nix-0.17.0/src/sys/signal.rs:764）+ `cannot find function mq_open/lio_listio/aio_cancel/shm_open` 等 51 处 | nix 0.17.0（2019）的 linux 分支把 `SigevThreadId` 的匹配臂 gate 在 `target_env="gnu"/"musl"`，`target_env="ohos"` 下无臂 → 非穷尽；libc 0.2.140+ 的 ohos 定义也不含 nix 旧版使用的部分 POSIX 符号。nix 首个含 `target_env="ohos"` 处理的版本是 0.28.0（0.27.1 及以前 0 处） | `nix = { version = "0.28.0", features = ["signal"] }`（nix ≥0.27 起 signal 等模块改为需要显式 feature）。weggli 仅用 `nix::sys::signal` 做 SIGPIPE 重置，调用签名 `signal(Signal, SigHandler)` 在 0.17/0.28 完全一致 → **未改动任何 weggli 源码行**。见 `patches/0002-Cargo.toml.patch` |
| 3 | `ld.lld: error: unable to find library -lstdc++`（链接 weggli bin/lib 时） | `build.rs` 用 `cc::Build::new().cpp(true)` 编译 `third_party/grammars/weggli-cpp/src/scanner.cc`，`cc` crate 默认发出 `cargo:rustc-link-lib=stdc++`；OHOS SDK 只提供 libc++（`ohos/native/llvm/lib/aarch64-linux-ohos/libc++.so`），无 libstdc++ | 构建环境设 `CXXSTDLIB=c++`（`cc` crate 官方支持的环境变量，见 cc 源码 `get_var("CXXSTDLIB")`），使 `cc` 发出 `-lc++`；clang 默认搜索路径已含 `llvm/lib/aarch64-linux-ohos` |
| 4 | `cargo probe failed: [Errno 13] Permission denied: …/rust-toolchain/bin/cargo` | Conan 包内 `bin/cargo` 为 0770；HMDFS 上 `chmod` 被拒绝（`chmod: Permission denied`，E046），OHOS 内核/加载器仍拒绝执行该未签名 ELF | 复制到 build_folder 私有目录后用 OHOS `binary-sign-tool sign -selfSign 1` 自签名（below/0.11.0 先例），签名后执行成功 |
| 5 | `Error loading shared library libssl.so / libcrypto.so`（cargo 启动时） | cargo 1.97 动态链接 `libssl.so`/`libcrypto.so`/`libz.so`，且需要 OpenSSL 3.5+ 的 `SSL_get0_group_name`；系统 `/usr/lib` 只有版本化 `.so.3` 且为 OpenSSL 3.0 | 解包 sha256 固定的 Harmonybrew OHOS bottle（openssl@3-3.6.4、zlib-ng-compat-2.3.3_1）到 build_folder，`LD_LIBRARY_PATH` 指向其 `lib/`（below/argc/alass 先例，R49：不写共享系统前缀） |
| 6 | `cargo build` 首次运行偶发 `rayon-core build-script-build … Text file busy (os error 26)` | HMDFS 上「刚写入的可执行文件立即 exec」的写回竞态（同目录其它 crate 编译并发时触发） | 重跑即通过（该错误不可复现，100 次立即 exec 与 8 并发×20 轮测试 0 失败）；配方以 `--locked` 顺序构建，未加任何绕过参数 |

### 未使用的绕过手段（明确记录）

- 未使用本地缓存顶替：所有依赖均走 conan 制品仓 / crates.io 镜像 / 官方 bottle；未使用 `--build=missing` 绕过依赖缺失（本次无缺失依赖）。
- 未修改 `Cargo.lock` 之外的任何上游构建输入；未修改依赖库源码（libc/nix 升级通过 semver 允许的 `cargo update -p … --precise`，知识 E358 口径）。
- 未改动 weggli 任何源码行（`.rs` 文件逐字节等于上游 tarball）。

## 源码修改

仅两个补丁，均为构建输入（无源码改动）：

| 补丁 | 内容 | 行数 |
|------|------|------|
| `patches/0002-Cargo.toml.patch` | `nix = "0.17.0"` → `nix = { version = "0.28.0", features = ["signal"] }` | +1/-1 |
| `patches/0001-Cargo.lock.patch` | 确定性锁图迁移：libc 0.2.112→0.2.155、nix 0.17.0→0.28.0（连带 bitflags/cfg_aliases 等），cargo 1.97.1 重新生成，保持 `--locked` | +34/-35 |

补丁不含任何平台宏（无 `__OHOS__` 注入），不注入共享系统前缀（R49/PF5/PF6 合规）。

## 依赖版本

| 依赖 | 版本 | 类型 | 来源 |
|------|------|------|------|
| rust-toolchain | 1.97.1 | 构建工具链（tool_requires） | ohpcd 制品仓（`conan download rust-toolchain/1.97.1 -r=ohpcd` rc=0，OHOS armv8 二进制 252.9MB） |
| openssl@3 | 3.6.4（bottle） | cargo 运行期共享库 | Harmonybrew OHOS bottle，sha256 `e1be73c6…b28f98` |
| zlib-ng-compat | 2.3.3_1（bottle） | cargo 运行期共享库 | Harmonybrew OHOS bottle，sha256 `1c17a31f…93a430` |
| crates.io 依赖 | 115 个（Cargo.lock） | Rust crate | rsproxy.cn 稀疏镜像（设备无 crates.io CA 链） |
| 系统库 | libc、libm、libdl、libpthread、libc++ | 目标系统库 | OHOS SDK sysroot |

无缺失依赖、无未发布依赖（W0/R36：`conan download` 实测可消费）。

## 验证结果

```bash
# 上游 Rust 套件（build() 内真实执行，计数取自 cargo 框架输出）
cargo test --release --locked --target aarch64-unknown-linux-ohos --lib --bins --tests -- --test-threads=1
# → lib 2 passed; bin 0 passed; cli.rs 9 passed; query.rs 45 passed ⇒ 56 passed / 0 failed / 0 ignored

# 上游 Python 绑定套件（Cargo feature python + pyo3 0.13.2，扩展模块 libweggli.so）
cargo build --release --locked --target aarch64-unknown-linux-ohos --features python
LD_PRELOAD=<libpython3.12.so.1.0> PYTHONPATH=<dir with weggli.so> python3 -m unittest tests -v
# → Ran 4 tests … OK（4 passed / 0 failed）

# test_package（消费者 + 鸿蒙特有，8 项）
conan create archives/w/weggli/0.2.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → HMBS_TEST_PACKAGE_RESULT={"status":"passed","discovered":8,"passed":8,"failed":0}
```

**上游测试实测总览（R51）**：60 用例全部真实执行，56 通过（Rust）+ 4 通过（Python），失败 0，跳过 0，漏测 0。
逐用例名称与日志路径见 `reports/upstream-tests.md`。

## 上游测试清点与未执行项

上游测试入口（4 个，全部接入）：

| 上游入口 | 用例数 | 是否执行 | 说明 |
|----------|--------|----------|------|
| `src/result.rs`、`src/util.rs`（lib 单测） | 2 | ✅ 已执行 | `cargo test --lib` |
| `tests/cli.rs`（CLI 集成，assert_cmd spawn 打包二进制） | 9 | ✅ 已执行 | `cargo test --tests` |
| `tests/query.rs`（查询语言语义矩阵） | 45 | ✅ 已执行 | `cargo test --tests` |
| `tests/__init__.py`（Python 绑定 unittest） | 4 | ✅ 已执行 | `--features python` + `python3 -m unittest tests`（需 LD_PRELOAD libpython，见下） |
| `benches/examples.rs`（criterion 基准） | 0（基准非用例） | ➖ 非测试入口 | 基准套件，不计入用例统计；`cargo test` 不选择 bench target |
| `third_party/examples/*.c`（4 个样例） | — | ✅ 作为 fixture 被 cli.rs/query.rs 用例消费 | `cluster.c` 等已被上游用例引用 |

- **doc-tests**：weggli `src/` 内 0 个 doctest 用例（`grep -c '```' src/lib.rs` = 0），且 `rust-toolchain/1.97.1` 载荷不含 rustdoc（cargo 无法 spawn，ENOENT；alass/martin/argc 同仓库判定为平台限制），故用 `--lib --bins --tests` 排除该空阶段，不丢任何用例。
- **Python 绑定的平台限制（已解决）**：OHOS 加载器要求扩展模块的 Python C API 符号（`PyList_New` 等）在全局作用域可见——pyo3 的 `extension-module` 模式刻意不链接 libpython，导致 `import weggli` 报 `Error relocating … PyList_New: symbol not found`。实测 `LD_PRELOAD=/storage/Users/currentUser/usr/local/lib/libpython3.12.so.1.0` 后 4 个用例全部通过（0.076s）。该限制与 weggli 无关，属 OHOS 加载器行为；细节与日志见 `reports/upstream-tests.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/weggli` | 6.1MB 级别 ELF（AArch64，OHOS），`weggli --version` → `weggli 0.2.4` |
| `share/weggli/README.md` | 上游 README |
| `licenses/LICENSE` | 上游 Apache-2.0 |
| `res/upstream_test_result.json` | build() 持久化的上游测试计数（test_package 依据它复发 HMBS_UPSTREAM_TEST_RESULT） |

## 注意事项

1. HMDFS 上 `chmod` 被拒绝、Conan 包内 ELF 即使 0770 也不可执行 → Rust 工具链二进制必须复制后自签名（`binary-sign-tool`）。
2. cargo 运行期需要 OpenSSL 3.5+ 的 `libssl.so`/`libcrypto.so`（未版本化名）；系统 OpenSSL 3.0 不满足。
3. `/tmp` 只读：构建与测试的临时目录统一落在 `${TMPDIR}`（默认 `~/.conan2/.../b/tmp`），test.sh 用 `mktemp -d "${TMPDIR:-$HOME/tmp}/…"`。
4. crates.io 直连无 CA 链，使用 `rsproxy.cn` 稀疏镜像 + 显式 `cainfo`（`/storage/Users/currentUser/usr/local/ssl/cert.pem`）。
5. weggli 无外网/在线数据集依赖，全部用例可离线执行。
## 知识沉淀

本次适配产生 2 条新知识草稿（kv + md 一一对应，提交 knowledge/drafts/）：

| 草稿 | 主题 |
|------|------|
| `E543-draft-3BD8` | Rust `build.rs` 经 `cc` crate 编译 C++ 时按 OHOS libc++ 重定向 `CXXSTDLIB=c++` |
| `E544-draft-AA24` | OHOS 加载器下 pyo3 扩展模块需显式预加载 libpython（`Error relocating … PyList_New: symbol not found`） |

既有知识复用：`E358`（旧 Rust Unix 依赖锁图在 OHOS target_env 下的确定性迁移）直接指导了
libc/nix 的最小升级与 `--locked` 复验；`E509` 类（cargo 运行期 OpenSSL 共享库）指导了 bottle 注入；
`E079/E046`（HMDFS 链接与权限）指导了工具链复制+签名路径。

## ### 对话 #

### 对话 #1 — 任务下发与适配决策（2026-10-01）

- 用户（Ran）以工作区 `/storage/Users/currentUser/Desktop/lan workspace` 下发目标库适配任务：
  `weggli 0.2.4`，前置条件「所有依赖已通过 conan download 验证可消费」，要求完整走通
  源码核验 → OHOS 适配 → 真实构建 → 上游测试（不漏测）→ test_package → conan create →
  conan-verify → finish → W2/W3 → PR 文件原子性检查，并在 commit/push/PR 前停止等待确认。
- R47 语言预检机器判定 `detected_language=rust`（cargo 构建系统 + 13 个 .rs 主体源文件，占比 81%）；
  与任务默认 cpp 不一致，但仓库 Rust 路径受支持（`rust-toolchain/1.97.1` 已发布为基础设施包，
  main 中已有 below/argc/alass/cbindgen 等 Rust 配方先例），故按 rust 分支继续适配并全程留证。
- 关键决策：① 只改构建输入（Cargo.toml/Cargo.lock），不改任何 weggli 源码行；
  ② 上游测试在 build() 内真实执行并持久化计数，test_package 复发证据；
  ③ 鸿蒙特有用例≥1（实际 3 项，H1/H2/H3）。
---

**编译结束**: 2026-10-01 17:06
**最终状态**: built
