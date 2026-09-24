# cargo-bash-completions

cargo 命令的 bash 补全脚本：在交互式 shell 里对 `cargo` 补全子命令（build、check、run、
test、add、install…）、各子命令的选项（`--release`、`--target`、`--manifest-path`…）、
`+toolchain` 以及目标三元组。

## 上游

- 仓库：<https://github.com/rust-lang/cargo>（Rust 官方 cargo，Apache-2.0 OR MIT）
- 交付文件：`src/etc/cargo.bashcomp.sh`（311 行 / 11443 字节）
- **版本号口径**：包版本 `1.97.0` = cargo CLI 对外版本（`cargo --version` 输出
  `cargo 1.97.0`，随 Rust 1.97.0 分发）。cargo 的 crate/tag minor **恒比所属 Rust 发行版大 1**
  （上游 `src/doc/contrib/src/process/release.md`: *"The minor version is always 1 greater
  than the Rust release it is a part of"*），故源码取官方 tag `0.98.0`
  （commit `c980f4866141969fab6254a680546a277789d6f0`，与 `rust-lang/rust` tag 1.97.0 的
  `src/tools/cargo` submodule 一致）。

## 包内容

| 路径 | 说明 |
|---|---|
| `share/bash-completion/completions/cargo` | 唯一功能产物：bash 补全脚本（无 shebang、非可执行，供 source） |
| `licenses/LICENSE-APACHE`、`licenses/LICENSE-MIT` | 上游双许可 |

无 `bin/`、`lib/`、`include/`（纯脚本包，R38 故不声明 `commands.json`）。

**本包不编译任何 Rust 代码**：只从上游源码树取出补全脚本安装为数据文件，构建机与 CI
均无需 rustc/cargo 工具链。

## 使用

由 bash-completion 的加载机制自动 source（文件名即命令名 `cargo`），或手工加载：

```bash
source <conan 包目录>/share/bash-completion/completions/cargo
complete -p cargo      # -> complete -F _cargo cargo
cargo bu<TAB>          # -> build
cargo build --rel<TAB> # -> --release
```

## 运行期依赖

- `bash`（`complete`/`compgen` 为 bash 内建，POSIX sh 无法加载；脚本使用 `[[ ]]`、
  `extglob`、`BASH_REMATCH` 等 bashism）
- `cargo`（被补全对象）：脚本顶部 `command -v cargo` 守卫，PATH 中没有 cargo 时
  **不会**定义 `_cargo`，也不会注册补全；子命令候选由 `cargo --list | awk` 实时生成
- `bash-completion` 框架：脚本调用其 helper `_get_comp_words_by_ref`、`_filedir`、
  `_comp_command_offset`（bash-completion ≥ 2.12 时用于转发第三方 `cargo-*` 子命令补全）
- `rustup` / `rustc`（可选）：仅 `+toolchain` 与 `--target` 补全时调用

框架只作加载与 helper 提供方，配方不声明 requires（与已发布同族包 `docker-completion`、
`pip-completion`、`brew-cask-completion` 一致）。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.97.0 | built | 首次适配：安装路径由 Rust 发行版的 `etc/bash_completion.d/`（共享系统前缀）改为包内私有 `share/bash-completion/completions/`，安装名 `cargo.bashcomp.sh` → `cargo`；无源码补丁 |
