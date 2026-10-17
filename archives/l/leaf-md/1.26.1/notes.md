# leaf-md 1.26.1 — 适配笔记（HarmonyOS PC / aarch64）

## 1. 软件与源码

| 项 | 值 |
|----|----|
| 名称 | leaf-md（上游仓库 `RivoLink/leaf`，可执行文件名为 `leaf`） |
| 版本 | 1.26.1 |
| 上游 | <https://github.com/RivoLink/leaf> |
| 语言 | Rust（cargo） |
| 许可证 | MIT |
| 源码包 | `https://github.com/RivoLink/leaf/archive/refs/tags/1.26.1.tar.gz` |
| sha256 | `fcff13393d749efe738688d1a31064081957e5e8712a1a883d897d3c29959c63` |

命名说明：本包在制品仓中的名字是 **leaf-md**，上游 crate / 可执行文件都叫 `leaf`。
`leaf-md` 来自 Homebrew formula 名（上游随后把 formula 改名为
`leaf-markdown-viewer`）。crates.io 上的 `leaf` crate 是**另一个**项目
（autumnai/leaf，最高 0.2.1），所以源码只能走 GitHub 官方 tag 归档，不能走
crates.io。包名与二进制名分离，因此 `commands.json` 里声明可执行文件为 `leaf`。

## 2. 依赖检查（W0）

`Cargo.toml` 的依赖全部是 crates.io crate，**没有任何 Conan 依赖**，因此本包
`requirements()` 为空。真正需要关心的是其中两个 crate 会编译 **C 代码**：

```
onig_sys 69.9.1  → cc-rs 编译 oniguruma（syntect 语法高亮用）
ring 0.17.14     → cc-rs 编译 ring 的汇编/C（rustls TLS 用）
```

这两者在 OHOS 上必须把 `cc-rs` 指向 OHOS clang，否则会用不存在的 `cc`。

## 3. 语言预检（R47）

```
$ ohc-run.py lang-preflight leaf-md 1.26.1 --src <src>
✅ 语言匹配: task=rust, detected=rust
```

判定依据：`Cargo.toml` + `Cargo.lock` 存在，`src/**/*.rs` 为主体，
`build.rs` 为 Rust，构建系统为 cargo → `detected_language=rust`，与任务语言一致。

## 4. 构建方式

OHOS PC 上的 rustc 宿主机三元组本身就是 `aarch64-unknown-linux-ohos`
（Harmonybrew 的 rust 1.98.1），所以**这是原生编译**，不需要 `--target`：
`cargo build --release` 产出的就是 OHOS aarch64 可执行文件。只需要告诉 cargo
用哪个 linker。

```toml
# .cargo/config.toml（由 conanfile.py 的 _configure_cargo() 生成）
[build]
target-dir = "<build_folder>/target"

[target.aarch64-unknown-linux-ohos]
linker = "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang"
```

`CC_aarch64-unknown-linux-ohos` 这个名字**带连字符**，不能写成 POSIX shell 的
前缀赋值（`VAR=x cmd` 只在变量名合法时可用），必须用 `env` 传递：

```bash
env CARGO_TARGET_DIR=<build>/target \
    CC_aarch64-unknown-linux-ohos=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
    CC_aarch64_unknown_linux_ohos=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
    CC=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
    cargo build --release --locked
```

## 5. 上游测试

上游测试**共 348 个 `#[test]`**（实测，逐文件计数见
`test_package/MANIFEST.yml`）：其中 334 个在 `src/tests/*.rs` 的
`#[cfg(test)]` 模块里，另有 8 个在 `src/markdown/markers.rs`、6 个在
`src/terminal.rs`（这两处不在 `src/tests/` 下，但不属于单元测试模块外的
集成用例）。没有 `tests/` 目录，也没有任何需要网络/外部服务的用例（都是
Markdown 解析、渲染、终端宽度计算、TOC、主题、编辑器按键等纯本地逻辑）。

本包把上游测试**集成进 `conanfile.py` 的 `build()`**（`upstream_test_in_build: true`），
所以每次 CI 构建都会完整重跑 348 个用例，而不是只在适配时跑一次。命令：

```bash
cargo test --release --locked --no-fail-fast
```

`--locked` 保证用上游 `Cargo.lock` 里的精确版本，避免 CI 上依赖漂移成另一个版本。

## 6. ELF 签名（必须）

OHOS 上未签名的可执行文件运行会报 `Operation not permitted`，所以
`package()` 里用 `binary-sign-tool` 自签名（先 `--remove-section .codesign`
清掉旧签名再签，避免重复签名失败）：

```bash
llvm-objcopy --remove-section .codesign <bin> || true
binary-sign-tool sign -inFile <bin> -outFile <bin>.signed -selfSign 1
```

`test_package/ohos_elf_check.py` 会把“签名存在（`.codesign` 段）”作为一项
鸿蒙特有断言来校验，防止签名步骤被漏掉却没人发现。

## 7. 踩坑记录

1. **包名 ≠ 二进制名**：包 `leaf-md`，产物 `leaf`。`test_package` 必须按
   `bin/leaf` 找产物；`commands.json` 里声明的是真实可执行的 `leaf`。
2. **crates.io 上有同名但不同项目的 `leaf`**（autumnai/leaf 0.2.1），
   不能用 crates.io 源码包，必须用 GitHub 官方 tag。
3. **`cargo test` 需要可执行的测试二进制**：测试进程也是 OHOS ELF，同样受
   平台约束；本地 W3 实测全部用例可正常执行。
4. **`get()` 的 filename 参数**：GitHub 归档 URL 带 `.tar.gz`，但为稳妥仍显式
   传 `filename=`，确保 conan 走 tar 解压分支而不是当普通文件落地。

## 8. 知识引用

- E180 —— Rust 在 OHOS 上原生编译（宿主三元组即 `aarch64-unknown-linux-ohos`，无需 `--target`）
- E340 —— Conan 打包 cargo 项目：`basic_layout` + 固定 `CARGO_TARGET_DIR` + `package()` 取 `target/release`
- E385 —— crate 的 `build.rs` 用 cc/cmake 编译 C 代码时，需把 CC/工具链指向 OHOS clang
- E358 —— `cargo --locked` 与 Cargo.lock 版本锁定的兼容性
- E186 —— cargo 产物在 musl/OHOS 上的 RUNPATH 与 `ldso` 加载问题

（草稿：见 `knowledge/drafts/`，本次适配产出的新增知识条目。）

---

## 9. 对话记录

### 对话 #1 — 2026-09-17

- 任务：适配 leaf-md 1.26.1（`feat/leaf-md-1.26.1` 分支）。
- 独立 worktree：`.worktrees/leaf-md-1.26.1`（detached HEAD `88890e94b2`）。
- 核名：`leaf-md` 是 Homebrew 配方名，对应上游 Rust 项目 `RivoLink/leaf`
  （在 Homebrew 已更名为 `leaf-markdown-viewer`）。PyPI 上不存在 `leaf-md`
  （实测 404），确认按 Rust 项目适配。
- 工具链：rustc/cargo 1.98.1（宿主三元组已是 `aarch64-unknown-linux-ohos`），
  `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER=clang`。
- 源码 SHA256 复核：`fcff1339…99c63`（两次独立下载一致）。
- 上游测试全量执行：`running 348 tests` → `348 passed; 0 failed; 0 ignored`。
- 踩坑：W3 首轮失败（zsh here-doc 用 `/tmp` 只读，须设 `TMPPREFIX`）；
  次轮失败（`conandata.yml` 注释里的裸 URL 被 CI 预下载正则匹配并改写，
  污染真实源码 URL）——已移除注释裸 URL 并在文件中写明原因。
- 最终状态：`built`（conan-verify 通过、W3 本地 CI 模拟通过）。
---

**编译结束**: 2026-09-17 18:07
**最终状态**: built
