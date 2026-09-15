# pip-completion

pip 命令的 bash 补全脚本：在交互式 shell 里对 `pip` / `pip2` / `pip3` 补全子命令
（install、download、uninstall、freeze、list…）以及各子命令的选项（`--upgrade`、
`--index-url`…）。

## 上游

- 仓库：<https://github.com/ekalinin/pip-bash-completion>（`ekalinin/pip-bash-completion`，MIT）
- 上游无 release/tag；版本号 `20200731` 由 Homebrew 依 commit
  `321d8bd2c56bb1565ac20210367bd272a111a1aa` 的日期自编，本仓库沿用同一版本口径，
  源码取 GitHub 官方 commit archive。

## 包内容

| 路径 | 说明 |
|---|---|
| `share/bash-completion/completions/pip` | 唯一功能产物：861 字节 bash 补全脚本（无 shebang、非可执行，供 source） |
| `licenses/LICENSE` | MIT |

无 `bin/`、`lib/`、`include/`（纯脚本包，R38 故不声明 `commands.json`）。

## 使用

由 bash-completion 的加载机制自动 source，或手工加载：

```bash
source <conan 包目录>/share/bash-completion/completions/pip
complete -p pip     # -> complete -o default -F _pip pip
pip in<TAB>         # -> install
```

## 运行期依赖

`bash`（`complete`/`compgen` 为 bash 内建，POSIX sh 无法加载）、`pip`（被补全对象，
随 `python/3.12.9` 分发）、`awk`/`grep`/`tr`（解析 `pip --help` 输出）。
`bash-completion` 仅作加载框架，脚本本身不调用其 helper 函数，故配方不声明 requires
（与 `docker-completion`、`brew-cask-completion` 两个已发布同族包一致）。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 20200731 | built | 首次适配：安装路径由上游 `/etc/bash_completion.d`（需 sudo）改为包内私有 `share/bash-completion/completions/`，无源码补丁 |
