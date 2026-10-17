# rhai 1.25.0 适配笔记

## 软件信息
- 上游仓库: https://github.com/rhaiscript/rhai（MIT OR Apache-2.0）
- 官网: https://rhai.rs ；crates.io: `rhai` 1.25.0（2026-05-24 发布）
- 语言: Rust（edition 2018，MSRV 1.66.0）；Cargo workspace（成员 `.`、`codegen`、`codegen/tests/custom_root`）
- 构建系统: cargo（纯 Rust，依赖闭包无任何链接外部 C 库的 `-sys` crate）
- 编译环境: HarmonyOS PC（aarch64），rustc/cargo 1.97.1（rust-toolchain/1.97.1 包，host target = aarch64-unknown-linux-ohos），OHOS SDK clang 15 作链接器
- 编译日期: 2026-10-01
- 版本溯源: GitHub tag `v1.25.0` = commit `8498f86907d238000b67a5fb3348250fd252b314`（`git ls-remote` EXIT=0）

## 源码与版本映射
- 官方源（R39/PF7）: `https://github.com/rhaiscript/rhai/archive/refs/tags/v1.25.0.tar.gz`
- SHA256 = `5862084ee0c55882b58cdbb9fbee66a5817eac8f4ef16e56bcb98b486e03f`（真机 `sha256sum` 实测，561141 bytes）
- 选用 GitHub tag tarball（而非 crates.io `.crate`）：仓库 `include = ["/src/**/*","/Cargo.toml","/README.md","LICENSE*"]` 只把 src 打包进 `.crate`，**不含 `tests/`**；要运行全部上游测试必须用完整仓库归档。

## 依赖前置（W0/R35/R36）
- 唯一强制第三方依赖：`rust-toolchain/1.97.1`（tool_requires），`conan download rust-toolchain/1.97.1 -r=ohpcd --only-recipe` → **EXIT=0（可消费）**
- 其余为 cargo 管理的 crates.io/git crate（非 conan 包）与系统库（libc/linux-raw-sys），不构成制品仓阻塞

## 上游测试用例申报（R51 三步法）

### 1. 上游测试清点（静态统计）

| 测试类型 | 用例数 | 来源 |
|----------|--------|------|
| 集成测试文件 | 58 | `tests/*.rs` |
| `#[test]` 函数（tests/） | 287 | `grep -rn '#\[test\]' tests/` |
| `#[test]` 函数（src/） | 1 | `src/lib.rs`（test_rational_multiply） |
| **静态合计** | **288** | 部分用例受 feature gate 约束 |

### 2. 上游测试实际运行（本机 = HarmonyOS PC，host=target）

命令：
```
cargo test --release --tests \
  --features testing-environ,decimal,serde,metadata,internals,debugging \
  --target aarch64-unknown-linux-ohos
```

**结果：281 通过 / 0 失败 / 0 忽略（61 个 test binary，通过率 100%）**

按套件（节选，完整见 `reports/test-report.md`）：
serde 26、functions 22、modules 13、string 10、arrays 9、maps 9、var_scope 9、
compound_equality 8、custom_syntax 8、method_call 8、optimizer 8、switch 8、
call_fn 7、closures 7、get_set 7 …（全部 0 failed）

补充运行同源 feature 组合 `testing-environ,unicode-xid-ident,decimal,serde,metadata,internals,debugging` → 同样 **281 通过 / 0 失败**（验证 gate 覆盖）。

日志：`.plan/rhai_build/upstream_tests.log`（容器内工作路径）

### 3. 失败用例逐项技术原因

无失败用例。

> doc-test 说明：`cargo test` 默认还会执行 rustdoc 文档测试，但 `rust-toolchain/1.97.1`
> 基础设施包不含 rustdoc 二进制，故以 `--tests` + `--lib` 显式覆盖全部测试目标并排除 doctest。

## 编译过程与平台适配（逐项真实错误 → 根因 → 修复）

工具链就绪：`conan install --requires=rust-toolchain/1.97.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`
→ 下载 `conan_package.tgz` 252.9MB，解包 441MB（含 `lib/librustc_driver-75adf430b23f8c75.so` 297MB）。
> 注：首次安装因缓存残留出现 `Couldn't remove folder ... Cannot change permissions for .../lib/rustlib`
> 与“包不完整”（缺 `lib/*.so`）。`rm -rf` 残留目录 + `conan remove` 后重装即恢复完整。

| # | 平台问题 | 首个真实错误（原始输出 / 退出码） | 根因 | 修复（配方内自动化） |
|---|----------|-----------------------------------|------|----------------------|
| 1 | 工具链二进制不可执行 | `permission denied: .../bin/cargo`（EACCES） | rust-lang dist 二进制无 OHOS code signature，且 `cp` 后丢失可执行位 | `_prepare_signed_toolchain()`：`binary-sign-tool -selfSign 1` 签名 cargo/rustc/librustc_driver，**签名输出丢失 +x，须再 `chmod 0o755`**（实测：仅签名不 chmod 仍 permission denied） |
| 2 | rustc 找不到 std | `error[E0463]: can't find crate for 'std'`（附误导提示 `rustup target add aarch64-unknown-linux-ohos`） | sysroot 的 `lib/rustlib` 是**软链**时 rustc 无法定位标准库 | 真实复制 `lib/rustlib/<target>/{lib,etc}`（跳过 bin/analysis 以减小体积）；**不可用软链** |
| 3 | 链接失败 127 | `aarch64-unknown-linux-ohos-clang[3]: readlink: inaccessible or not found` → `exit status: 127` | SDK clang 是 shell 包装脚本，用 `readlink`/`dirname`；构建 PATH 覆盖时丢了 `/usr/bin` | PATH 前置工具链 bin，但**保留 `/usr/bin`/`/bin`** |
| 4 | cargo 无法启动 | `Error loading shared library libssl.so (needed by cargo)` | cargo 动态链接 libssl/libcrypto/libz；OHOS loader 忽略 DT_RUNPATH，且**不解析软链形式的 DT_NEEDED** | `_prepare_runtime_libs()`：harmonybrew openssl@3-3.6.4_1 / zlib-ng-compat-2.3.3_2 bottle（sha256 校验），按 SONAME 提供**实体文件**（libssl.so/libssl.so.3/libcrypto.so/libcrypto.so.3/libz.so/libz.so.1）并签名 chmod，前置进 LD_LIBRARY_PATH |
| 5 | cargo 解析阶段访问 github | `fatal: unable to access 'https://github.com/schungx/rustyline/': Failed to connect ... 65396 ms` | 上游 `[patch.crates-io]` 把 rustyline 指向第三方 git fork，cargo 解析期强制拉取 | `patches/0001-drop-rustyline-git-patch.patch` 去除该段（该 fork 仅为 rhai-repl 的 Windows 括号粘贴；本包不构建 bin-features） |
| 6 | 设备无默认 CA | cargo sparse 索引 `CERTIFICATE_VERIFY_FAILED` | 设备无默认 CA store | `_ca_bundle()` 探测系统 `cacert.pem` → `SSL_CERT_FILE`/`CURL_CA_BUNDLE` + `$CARGO_HOME/config.toml` cainfo；crates 走 `rsproxy.cn` sparse 镜像 |
| 7 | OHOS /tmp 只读（E002） | cargo 临时文件写入失败 | `/tmp` 为只读 erofs | `_ensure_writable_tmpdir()`：已有可写 TMPDIR 则不动，否则落 `~/tmp/rhai` |
| 8 | 无 cc 符号链接 | rustc 默认链接器不可用 | 设备无 `cc` | `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER` = OHOS SDK `aarch64-unknown-linux-ohos-clang` |
| 9 | rustup 不可用（E105/E154） | `unrecognized OS type: HarmonyOS` | 标准 rustup 不识别 HarmonyOS 宿主 | 全程禁用 rustup 引导，工具链由 `tool_requires` 提供 |

## 源码修改

仅 1 处（非平台代码改动）：删除 `Cargo.toml` 的 `[patch.crates-io]`（见上表 #5）。
其余上游源码零修改。

## 依赖版本
- rustc/cargo 1.97.1（rust-toolchain/1.97.1，aarch64-unknown-linux-ohos）
- OHOS SDK clang 15（链接器）
- crate 由 cargo 按 semver 从 crates.io（rsproxy 镜像）解析（仓库无 Cargo.lock；`Cargo.msrv.lock` 对 1.25.0 已过期，仅作名单参考）

## 验证结果

```bash
# 上游测试（真机 host=target）
cargo test --release --tests \
  --features testing-environ,decimal,serde,metadata,internals,debugging \
  --target aarch64-unknown-linux-ohos
# 281 passed; 0 failed; 0 ignored → 通过率 100%

# 构建产物
cargo build --release --bins --features debugging --target aarch64-unknown-linux-ohos
# bin/rhai-run, bin/rhai-dbg
```

### 消费者功能测试（test_package/test_rhai.py）

断言 11 项（全部通过）：
- 消费者功能 7 项：A0/A1 产物存在、A2 脚本执行 rc=0、A3 输出 `sum=45`、A4 输出 `42`、A5 语法错误报 `Syntax error`、A6 缺失文件 rc≠0
- 鸿蒙特有 4 项：B1 ELF machine=AArch64(183) / B2 PT_INTERP=`/lib/ld-musl-aarch64.so.1` / B3 含 OHOS code signature / B4 非空可执行
---

**编译结束**: 2026-10-01 15:20
**最终状态**: built
