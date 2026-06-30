# zsh-history-substring-search

## 简介

zsh-history-substring-search 是一个 ZSH 插件，实现了类似 Fish shell 的历史搜索功能。用户可以输入命令的任意部分，然后按上下箭头键循环匹配历史记录中的命令。

## 特性

- 🎯 子字符串搜索：输入命令的任意部分进行历史搜索
- ⬆️⬇️ 方向键绑定：直观的上下箭头键导航
- 🎨 高亮显示：匹配的命令会高亮显示
- 🔧 可配置：支持多种配置选项

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.1.0 | ✅ built | 2026-05-25 | 纯脚本插件，无需编译 |

## 安装

### 使用预编译包

```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- zsh-history-substring-search 1.1.0
```

### 手动安装

```bash
# 将插件文件复制到 zsh 插件目录
cp -r zsh-history-substring-search ~/.oh-my-zsh/custom/plugins/

# 在 ~/.zshrc 中启用插件
plugins=(zsh-history-substring-search)

# 重新加载配置
source ~/.zshrc
```

## 使用

在 ZSH 命令行中：
1. 输入命令的任意部分
2. 按 ↑ 键向上搜索匹配的历史命令
3. 按 ↓ 键向下搜索匹配的历史命令
4. 按 Ctrl+U 取消搜索

## 配置

在 `~/.zshrc` 中添加以下配置：

```zsh
# 高亮匹配的命令（默认：白字洋红底）
HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND='bg=magenta,fg=white,bold'

# 高亮未匹配的命令（默认：白字红底）
HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_NOT_FOUND='bg=red,fg=white,bold'

# 不区分大小写搜索（默认）
HISTORY_SUBSTRING_SEARCH_GLOBBING_FLAGS='i'

# 启用模糊搜索
HISTORY_SUBSTRING_SEARCH_FUZZY=true

# 只匹配命令开头
HISTORY_SUBSTRING_SEARCH_PREFIXED=true
```

## 依赖

- ZSH 4.3 或更新版本

## 许可证

BSD 3-Clause License

## 相关链接

- GitHub: https://github.com/zsh-users/zsh-history-substring-search