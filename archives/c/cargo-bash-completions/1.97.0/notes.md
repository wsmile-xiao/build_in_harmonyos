# cargo-bash-completions 1.97.0 适配笔记

## 编译环境
- 构建系统: custom（无构建/打包族：交付物为上游源码树中的一个 bash 脚本，安装 = 复制）
- 编译日期: 2026-09-21
- 编译器: 无（包内无 C/C++/Rust 编译单元，不调用 clang/clang++/rustc）
- 状态: built
- 依赖: 0 个（`requires` / `tool_requires` 均为空）

## 源码获取

| 项 | 值 |
|---|---|
| 官方 URL | `https://github.com/rust-lang/cargo/archive/refs/tags/0.98.0.tar.gz` |
| 归档大小 | 4441392 字节 |
| sha256 | `7c11186fb61d20a8237b777b35beedd224c1103934f35b85fdd64ea2a9c77f07` |
| tag commit | `c980f4866141969fab6254a680546a277789d6f0` |
| 交付文件 | `src/etc/cargo.bashcomp.sh`（311 行 / 11443 字节） |

### 版本映射（R37；本次踩坑点，见问题表 #2）

cargo 的 **crate/tag 版本恒比其所属 Rust 发行版大一个 minor**，上游自述原文
（`src/doc/contrib/src/process/release.md`）：

> "Cargo's library is permanently unstable, so its version number starts with a `0`.
> The minor version is always 1 greater than the Rust release it is a part of,
> so cargo 0.49.0 is part of the 1.48 Rust release."

因此：**包版本 1.97.0（= cargo CLI 对外版本，随 Rust 1.97.0 分发）→ 仓库 tag `0.98.0`**。
`0.97.0` 属于 Rust **1.96**，不是本包版本。

三重交叉验证：

1. 上游文档规则（上引原文）；
2. `rust-lang/rust` tag `1.97.0` 的 `src/tools/cargo` submodule 指向
   commit `c980f4866141969fab6254a680546a277789d6f0`
   （`GET /repos/rust-lang/rust/contents/src/tools/cargo?ref=1.97.0`），
   该 commit 正是 cargo tag `0.98.0`；
3. 内容差异实证：`0.98.0` 的脚本第 51 行为 `local opt_mani='-m --manifest-path'`，
   而 `0.97.0` 为 `local opt_mani='--manifest-path'` —— `-m` 是 cargo 1.97 新增的短选项。
   test_package **A8** 断言就用它做版本实证；对 1.96 脚本反向实测该断言失败（见验证结果）。

## R47 语言预检（两轮，证据留档 reports/）

| 口径 | 命令 | rc | detected | 证据文件 |
|---|---|---|---|---|
| 默认（task=cpp） | `lang-preflight cargo-bash-completions 1.97.0 --src $BUILD_SRC_DIR` | 2 | `rust`（`build_system=cargo`，`Cargo.toml`，源文件 1440 个 rust:1437/bash:6/python:2/nodejs:1，主体 100%） | `reports/lang-preflight-default.log` |
| 如实（task=rust） | 同上 `--lang rust` | 0 | `rust` — 语言匹配，继续主流程 | `reports/lang-preflight-rust.log` |

判定说明：上游**仓库**确为 Rust（检测器结论正确，如实采纳 `--lang rust`），但本包
**不编译任何 Rust 代码**——只从源码树取出一个 bash 补全脚本作为数据文件安装，
构建机与 CI 均无需 rustc/cargo 工具链。这与"需要 cargo 构建的 Rust 应用包"（CI 能力
矩阵 Rust ❌，应报 `env_unsupported`）性质不同。社区对"上游语言 ≠ 交付物语言"的
数据/脚本包已有一致口径：显式声明真实语言后继续适配，并保留默认口径证据
（先例：`archives/c/cronic/3` 与 `archives/p/pari-galpol/20180625` 用 `--lang other`、
`archives/c/crunch64/0.6.2` 用 `--lang rust`、`archives/d/d-shlibs/0.109` 用 `--lang bash`）。
本次经验已沉淀为知识草稿 `knowledge/drafts/E999-draft-351D`。

## 编译步骤

无 configure / make / cargo 步骤。配方 `build()` 只做**源码核验**（不伪造编译）：

1. 断言 `src/etc/cargo.bashcomp.sh` 存在；
2. 断言体积 ≥ 4096 字节（实测 11443）；
3. 断言脚本仍含注册语句 `complete -F _cargo cargo`（上游若改名/改注册方式，构建立即失败，
   避免交付一个不生效的补全脚本）。

`package()` 把脚本安装到包内私有 `share/bash-completion/completions/cargo`，
并附上游双许可 `LICENSE-APACHE` / `LICENSE-MIT`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 下载失败：`Remote end closed connection without response`；`curl --retry` 亦 `curl: (28) timeout` / `OpenSSL SSL_read: unexpected eof` | 构建机到 `github.com` 的直连不稳定（与 `rust-toolchain/1.97.1` 归档记录的"官方源国内直连超时/限速"同因） | 换通道取得**同一官方归档**（`codeload.github.com` 是 `github.com/archive` 的后端，字节一致），置于 `init-build` 期望路径后重跑 → 命中"tarball 已存在"分支。conandata.yml **只写官方 URL**（R39/PF7），镜像回退交给 CI 预下载步骤 |
| 2 | **版本映射初版写反**：首版取 tag `0.97.0` 并在文档里写成"tag 比 CLI 版本小一个 minor"，实际交付的是 **Rust 1.96** 的脚本 | 凭 cargo "crate 0.x ↔ CLI 1.x" 的印象推断方向，未核上游文档 | W4 独立审计（P1）拦下。按上游 `release.md` 原文（minor = Rust minor + 1）改取 tag `0.98.0`，重算 sha256；并补交叉验证（rust 1.97.0 的 cargo submodule = `c980f486…` = tag 0.98.0）与内容实证（1.97 新增 `-m` 短选项）。**新增 A8 断言**把版本正确性固化进测试，对 1.96 脚本反向实测失败 |
| 3 | 上游补全脚本文件名不是惯例的 `cargo.bash` | 现代 cargo 改名为 `src/etc/cargo.bashcomp.sh`（另有 zsh 版 `src/etc/_cargo`，不属本包） | 按实际路径取文件；安装时重命名为 `cargo`（bash-completion 规范：文件名 = 被补全命令名，与 Rust 官方发行版的 `etc/bash_completion.d/cargo` 一致） |
| 4 | 上游没有安装该脚本的 make 目标；Rust 发行版把它装进 `etc/bash_completion.d/`（共享系统前缀） | Rust 用 rust-installer 安装，前缀由安装器决定 | 改落包内私有 `share/bash-completion/completions/cargo`（R49：禁止写 `/etc`、`/usr/local` 等共享前缀），与已发布同族包 `docker-completion` / `pip-completion` 完全同构 |
| 5 | 消费者测试首版 A4（负向守卫）误报：`bash: command not found` | 夹具把 `PATH` 在**外层**清空后再调 `bash`，导致连解释器都找不到——不是被测脚本的问题 | 改为在子 shell **内部**收窄 `PATH`（`bash -c 'PATH="$2"; source "$1"; …'`）；`source`/`declare`/`echo` 均为 bash 内建，空 PATH 下仍可用 |
| 6 | 补全脚本无法脱离 bash-completion 框架单独驱动（调用 `_get_comp_words_by_ref`/`_filedir`/`_comp_command_offset`） | 上游脚本设计为由框架加载 | test_package 自带**轻量桩**提供这三个函数（桩内不得 `local`，依 bash 动态作用域写回 `_cargo()` 的 `local cur prev words cword`），保证 CI clean 环境（未装 bash-completion）可复现 |
| 7 | 子命令候选依赖真实 `cargo --list`，而构建机/CI 无 cargo | 脚本 `_ensure_cargo_commands_cache_filled()` 执行 `cargo --list \| awk 'NR>1 {print $1}'`；且脚本顶部有 `command -v cargo` 守卫 | test_package 提供固定输出的 **cargo 桩**（`--list` 返回 build/check/run/test），既满足守卫又能断言补全候选被真实生成；同时用"无 cargo"场景做负向断言（A4）。经验已沉淀为草稿 `DRAFT-cargo-bash-completions-1.97.0-completion-test-double-stub` |
| 8 | `finish` 的 W3 预下载把 `conandata.yml` 改写成 `[镜像, 官方]` URL 列表后**未还原**，并残留 `.ghfast-bak` / `.orig` | W3 走 `ci/conan/build_and_test.sh` 预下载路径，该路径缺少 `conan-verify` G2 那样的"注入—还原"闭环 | 提交前 `git checkout -- conandata.yml` 还原并删除备份残留；已写入 SKILL_FEEDBACK 建议工具侧加 `trap EXIT` 还原 + finish 收尾自检（否则镜像 URL 会被 PF7 拦或直接进仓） |

## 源码修改

无。`patches/` 为空（`patches: {}`），不涉及平台宏（R8/PF5 无涉）。

## 依赖版本

配方无 `requires` / `tool_requires`（W0 结论：Depends = 0，PF4 无待验依赖）。

运行期依赖（不进 conan 依赖图，与同族先例一致）：

| 依赖 | 作用 |
|---|---|
| `bash` | `complete`/`compgen` 为 bash 内建；脚本使用 `[[ ]]`、`extglob`、`BASH_REMATCH` 等 bashism |
| `cargo` | 被补全对象；无它则守卫生效不注册（A4 已验证） |
| `bash-completion` | 提供 `_get_comp_words_by_ref`/`_filedir`/`_comp_command_offset` helper |
| `rustup` / `rustc`（可选） | 仅 `+toolchain`、`--target` 补全时调用 |

## R51 上游测试清点申报表

| 项 | 数量 | 清点方式与证据 |
|---|---|---|
| 针对**交付物**（`cargo.bashcomp.sh`）的上游自动化测试 | **0** | `grep -rn "bashcomp" <src> --include='*.rs' --include='*.toml' --include='*.sh' --include='*.md' --include='Makefile*'` → 唯一命中 `triagebot.toml:111 trigger_files = ["src/etc/_cargo", "src/etc/cargo.bashcomp.sh"]`（PR 打标签配置，非测试）；`find <src>/tests -iname '*completion*'` → 0 命中 |
| cargo **本体**的上游测试（与本包交付物无交集） | 152 个测试文件 / 4292 个 `#[cargo_test]` | `ls tests/testsuite/*.rs \| wc -l` = 152；`grep -rho '#\[cargo_test' tests/ \| wc -l` = 4292；另有 `tests/build-std` |
| 上游测试实际运行 | 未运行（如实声明） | **具体技术原因**：入口为 `cargo test`，需 rustc + cargo 工具链；本构建机与仓库 CI（远端 clean 环境）均无 Rust 工具链（W0b CI 能力矩阵：Rust ❌）。且这些测试验证的是 cargo **二进制**行为，本包既不构建也不交付 cargo 二进制 —— 故不计入本包上游用例基数（基数以交付物为界 = 0） |
| 对交付物可机器化执行的上游验证入口 | 2，**均实跑 rc=0** | `bash -n src/etc/cargo.bashcomp.sh`；`bash -c 'source <installed>/cargo && complete -p cargo'` → `complete -F _cargo cargo` |
| 适配补全的测试（test_package） | **8**（A1–A8，通过率 8/8 = 100%） | `bash test_cargo_completion.sh <completion_file>`，已在 `conan create` 内由 Conan 真实调用 |

## 验证结果

```bash
# 1) R47 语言预检（如实口径）
$ python3 scripts/ohc-run.py lang-preflight cargo-bash-completions 1.97.0 \
      --src $BUILD_SRC_DIR --lang rust
✅ 语言匹配: task=rust, detected=rust — 继续适配主流程      # rc=0

# 2) 版本映射交叉验证
$ curl -s https://api.github.com/repos/rust-lang/rust/contents/src/tools/cargo?ref=1.97.0 \
      | grep '"sha"'
"sha":"c980f4866141969fab6254a680546a277789d6f0"            # = cargo tag 0.98.0

# 3) 上游可执行验证入口（对交付物）
$ bash -n $BUILD_SRC_DIR/src/etc/cargo.bashcomp.sh          # rc=0，无输出

# 4) test_package 8 个断言（本机直跑，随后由 conan create 再跑一次）
$ bash archives/c/cargo-bash-completions/1.97.0/test_package/test_cargo_completion.sh \
      $BUILD_SRC_DIR/src/etc/cargo.bashcomp.sh
PASS: A1 completion file exists and is non-empty
PASS: A2 size sane (11443 bytes >= 8192)
PASS: A3 bash -n syntax check
PASS: A4 'command -v cargo' guard suppresses registration when cargo is absent
PASS: A5 completion registered: complete -F _cargo cargo
PASS: A6 _cargo() produced sub-command candidates: build check run test
PASS: A7 'cargo build --' produced option candidates (--release/--target/--manifest-path)
PASS: A8 '-m' short option present (cargo 1.97 feature; proves tag 0.98.0 script)
test_cargo_completion.sh: ALL PASSED (8/8)                  # rc=0

# 5) A8 反向验证（对 cargo 0.97.0 = Rust 1.96 的脚本，断言必须失败）
$ bash .../test_cargo_completion.sh /root/tmp/cargo-0.97.0/src/etc/cargo.bashcomp.sh
FAIL: A8 '-m' (1.97 新增) 未出现在候选中 —— 交付脚本可能来自错误的上游 tag
test_cargo_completion.sh: 1 FAILED                          # rc=1，证明断言有效

# 6) Conan 配方验证（G1/G2/G3/G4 + L2/L4/L5）与 W3 本地 CI
$ python3 scripts/ohc-run.py conan-verify cargo-bash-completions 1.97.0
✅ 配方验证通过；G2 conan create 内 test_package 实跑 8/8
$ python3 scripts/ohc-run.py finish cargo-bash-completions 1.97.0 built
W2 结构 / R36 依赖 / W3 本地 CI 通过 → .ci-result.json exit_code=0
```

> 完整原始日志见 `reports/conan-create.log` 与 `reports/w3-local-ci.log`
> （用 `grep -n "PASS: A\|ALL PASSED" reports/*.log` 定位，不在此写死行号）。

**aarch64 实跑说明**：本包产物是**架构无关的 bash 脚本**，无 ELF 可执行文件，因此
不存在"x86 runner 上跑 aarch64 二进制"的问题，也无需 qemu-aarch64 —— 上表测试均在
真实解释器（bash）中完整执行，不是 skip。包的 `package_id` 已 `self.info.clear()`，
os/arch/compiler/build_type 不参与标识。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `share/bash-completion/completions/cargo` | 11443 B | 唯一功能产物：cargo 的 bash 补全脚本（无 shebang、非可执行，供 `source`） |
| `licenses/LICENSE-APACHE` | — | 上游许可（Apache-2.0） |
| `licenses/LICENSE-MIT` | — | 上游许可（MIT） |

无 `bin/`、`lib/`、`include/` → 纯数据/脚本包，**不声明 `commands.json`**（R38；PF8 对
纯库包要求"必须没有"）。

## 注意事项

- 上游脚本的 `_get_targets()` / `_toolchains()` 会调用 `rustc` / `rustup`，
  未安装时这两类补全为空，不影响子命令与选项补全（A6/A7 覆盖）。
- 上游若把 `src/etc/cargo.bashcomp.sh` 改名或改变注册方式，`build()` 的第 3 项断言会
  直接让构建失败，而不是静默交付一个不生效的脚本。
- 后续升级版本时**务必重算 tag**：`cargo CLI X.Y.Z` → `tag 0.(Y+1).Z`，并用
  `rust-lang/rust` 对应 tag 的 `src/tools/cargo` submodule sha 复核。
- 本包与仓库中 `rust-toolchain/1.97.1` 无依赖关系：cargo 补全脚本是数据文件，
  安装后是否有 cargo 可用由使用者环境决定。
---

**编译结束**: 2026-09-21 19:32
**最终状态**: built
