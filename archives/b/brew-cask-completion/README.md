# brew-cask-completion

Homebrew Cask shell 补全脚本，为 bash 和 fish 提供 brew-cask 命令的自动补全支持。

- **许可证**: BSD-2-Clause
- **源码仓库**: https://github.com/xyb/homebrew-cask-completion
- **分类**: shell-completion

## 说明

此软件提供以下补全脚本：
- **Bash补全**: `homebrew-cask-completion.bash` → 安装到 `share/bash-completion/completions/brew-cask`
- **Fish补全**: `brew-cask.fish` → 安装到 `share/fish/vendor_completions.d/brew-cask.fish`

注意：不包含zsh补全，zsh用户需使用 oh-my-zsh。

## 编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1 | built | 2026-05-21 | 纯补全脚本包，创建Makefile支持DESTDIR安装 |

## 特殊说明

- 纯补全脚本包，无需编译步骤
- 实际源码仓库为 xyb/homebrew-cask-completion（非Homebrew组织）
- 安装流程仅为复制补全脚本到标准路径