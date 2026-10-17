# zizmor 1.27.0 适配笔记（HarmonyOS PC / aarch64-unknown-linux-ohos）

目标：`aarch64-unknown-linux-ohos`（OHOS aarch64 / armv8，clang 15，libc++，Release）。

## 1. 上游与源码

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/zizmorcore/zizmor |
| 版本 | 1.27.0（GitHub tag `v1.27.0`，release published 2026-07-14） |
| 源码 | https://github.com/zizmorcore/zizmor/archive/refs/tags/v1.27.0.tar.gz |
| sha256 | `2ef4347065e91b9a07c337d7161085b494866b5239605440b457cdcda4318136` |
| 构建系统 | cargo（workspace resolver=2 / edition=2024 / rust-version=1.88.0） |
| 语言（R47） | `rust`（manifest = Cargo.toml；148 个 .rs 主体源文件，占比 92%） |

> crates.io **无** 1.27.0（版本从 1.26.1 跳到 1.28.0，直查 1.27.0 → HTTP 404），
> 源码唯一来源为 GitHub archive tarball。

## 2. 依赖

* Conan 层唯一强制第三方依赖 = `rust-toolchain/1.97.1`（T，tool_requires），
  `conan download -r=ohpcd` 配方级 + OHOS/armv8 二进制级均 rc=0（可消费）。
* 其余全部 crate（50 直接 + 388 传递）走 crates.io（rsproxy.cn 稀疏镜像）。
* 无 `links` 类系统绑定 crate（openssl-sys / libz-sys / libgit2-sys / curl-sys /
  sqlite3-sys 均不存在）；native 代码随 crate 自带，由 `cc`/`cmake` 现场编译。

## 3. 平台问题与最小修复

### 3.1 jemalloc 在 HarmonyOS 上 SIGSEGV（→ patches/0001）

现象（修复前）：

| 场景 | 命令 | 结果 |
|---|---|---|
| CLI 审计 | `zizmor --no-progress --offline <wf.yml>` | rc=139（SIGSEGV），**10/10 必崩**（正确输出已打印，崩溃发生在退出路径） |
| `--version` / `--help` | clap 提前 `process::exit` | rc=0（不触发目标路径） |
| zizmor bin 单元测试 | `cargo test -p zizmor --bin zizmor` | 93/148 用例 SIGSEGV（非确定性，两轮 28 例翻转） |
| 其它 crate 测试二进制（不链 jemalloc） | yamlpatch 等 | 全绿 |

定位过程：

1. 禁用 `#[global_allocator] static GLOBAL: tikv_jemallocator::Jemalloc`
   → 测试二进制 93 例崩溃全部消失（只剩 21 例 rc=101 的 GH_TOKEN 门控 panic）。
2. 保留 jemalloc 但开启 `disable_initial_exec_tls`
   → CLI 崩溃消失，测试二进制仍崩 → 不是 TLS 模型单点问题。
3. 结论：**jemalloc 的线程缓存/TSD 析构路径在 HarmonyOS 上不可用**（进程退出、
   tokio 多线程运行时析构、libtest 回收测试线程三个场景均可复现）。

最小修复（`patches/0001-ohos-use-system-allocator.patch`，2 处 cfg，无逻辑改动）：

* `crates/zizmor/Cargo.toml`：目标依赖表增加 `not(target_env = "ohos")`；
* `crates/zizmor/src/main.rs`：`#[global_allocator]` 的 cfg 增加
  `not(target_env = "ohos")`。

修复后：CLI 审计连续 8/8 rc=0；测试二进制 127 passed / 0 failed。

### 3.2 aws-lc-sys 汇编缺失（→ 配方注入 CMAKE_TOOLCHAIN_FILE）

首个真实错误（链接期）：

```
ld.lld: error: undefined symbol: aws_lc_0_41_0_ChaCha20_ctr32_neon
ld.lld: error: undefined symbol: aws_lc_0_41_0_aes_hw_encrypt
ld.lld: error: undefined symbol: aws_lc_0_41_0_vpaes_encrypt
ld.lld: error: undefined symbol: aws_lc_0_41_0_bignum_copy_row_from_table_16
```

CMake 配置期的根因行：

```
System is unknown to cmake, create: Platform/HarmonyOS ...
-- Unknown processor found. Using generic implementations. Processor: unknown
-- Detected generic linux platform. No assembly files will be included.
```

根因：OHOS 的 `uname -s` 返回 `HarmonyOS`，CMake 无 `Platform/HarmonyOS.cmake`
→ `CMAKE_SYSTEM_PROCESSOR` 为空 → aws-lc 的 CMakeLists 判定 `ARCH=generic`
→ `generated-src/linux-aarch64/` 预生成汇编不参与编译 → `libaws_lc_*.a` 内
只有 `.c.obj`（254 个对象、0 个 `.S.obj`）→ 链接期 asm 符号未定义。

修复：aws-lc-sys 0.41 的 `configure_open_harmony()` 只在自己未设置时才覆盖
`CMAKE_TOOLCHAIN_FILE`，因此配方在 `build()` 写入最小工具链文件
（`ohos-aarch64.cmake`：`CMAKE_SYSTEM_NAME Linux` + `CMAKE_SYSTEM_PROCESSOR
aarch64`）并注入环境变量。修复后 CMake 输出
`Copying platform assembly files from .../generated-src/linux-aarch64/crypto/`。

### 3.3 e2e::issue_1745 快照（→ build() 补 `.git` 标记）

上游集成快照 `e2e::issue_1745` 断言 repo-root 相对路径渲染；zizmor 通过
`registry/input.rs::discover_root` 向上查找 `.git` **目录**定位仓库根。发行
tarball 不含 `.git`，`best_identifier` 退化为“相对输入目录” → 快照不匹配
（实际 `workflows/test.yml`，期望含 `.github` 前缀）。`build()` 在跑测试前创建
`.git` 标记目录即可（无需真实 git 元数据）；实测该用例由 FAILED 转 ok。

### 3.4 构建环境注意（本地）

* 工作区路径 `.../lan workspace` 含空格 → jemalloc 的 autoconf `configure`
  报 `configure: error: failed to load site script .../lan`；构建树迁到无空格
  路径后消失（本地环境问题，conan 缓存路径 `/storage/Users/currentUser/.conan2`
  无空格，不受影响）。
* HMDFS + `umask 077 && mktemp -d "./confXXXXXX"` 生成 `drwx--S---` 目录不可写
  （E011/E114）；3.1 的 jemalloc 排除同时消除了该 crate 的 autoconf 调用。

## 4. 上游测试（R51 三步法）

命令（配方 `build()` 内真实执行）：

```
cargo test --release --locked --target aarch64-unknown-linux-ohos \
    --features schema --lib --bins --tests
```

清点（静态）：workspace 内 `#[test]`/`#[tokio::test]` 属性 617 处，
测试入口 = 15 个 cargo 测试目标（8 个 crate 的 lib 单测 + 5 个 `tests/` 目录
集成 + zizmor bin 单测 + zizmor 大集成套件）。

实测（真机，HarmonyOS PC）：**562 passed / 0 failed / 35 ignored**（rc=0）。
逐目标计数见 `test_package/MANIFEST.yml` 的 `upstream_test_audit` 段，
逐用例名称与日志见 `reports/upstream-tests.md`。

未纳入门禁（环境前置缺失，已逐一说明）：

| 门控 | 用例数 | 缺失前置 |
|---|---|---|
| `gh-token-tests` / `online-tests`（crater-tests 传递启用） | 21 | 真实 GH_TOKEN + GitHub API |
| `tty-tests` | 依赖 expect/unbuffer | 未安装 |
| `crater-tests` | 联网克隆上游仓库 | 无外网 GitHub 访问 |
| Doc-tests | — | `rust-toolchain/1.97.1` 不含 rustdoc 可执行文件 |

## 5. 对话

### 对话 #1 — 任务下发与适配决策（2026-10-02）

- 用户（Ran）以工作区 `.../lan workspace` 下发目标库适配任务：`zizmor 1.27.0`，
  前置条件“所有依赖已通过 conan download 验证为可消费”，要求完整走通
  源码核验 → OHOS 适配 → 真实构建 → 上游测试（不漏测）→ test_package →
  conan create → conan-verify → finish → W2/W3 → PR 文件原子性检查，
  并在 commit/push/PR 前停止等待确认。
- R47 语言预检机器判定 `detected_language=rust`（cargo + 148 .rs，占比 92%）；
  与任务默认 cpp 不一致，但本仓库 Rust 路径受支持（`rust-toolchain/1.97.1`
  已发布为基础设施包，main 中已有 below/argc/alass/cbindgen 等 Rust 配方先例），
  故按 rust 分支继续适配并全程留证。
- 关键决策：① 只改构建输入（目标依赖表 + allocator cfg），不改任何 zizmor 逻辑；
  ② 上游测试在 build() 内真实执行并持久化计数，test_package 复发证据；
  ③ 鸿蒙特有用例 ≥1（实际 3 项，H1/H2/H3）。
---

**编译结束**: 2026-10-02 16:46
**最终状态**: built
