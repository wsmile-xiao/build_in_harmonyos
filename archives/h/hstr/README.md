# hstr - History Suggest Box

## 简介

hstr（History Suggest Box）是一个命令行工具，用于在 Bash 和 Zsh 中提供 shell 命令历史的建议框功能。它提供了更好的高亮、导航、搜索体验，让用户能够快速查找和执行历史命令。

## 功能特性

- **命令历史搜索**：快速搜索和过滤历史命令
- **智能建议**：基于历史使用频率提供命令建议
- **高亮显示**：命令关键词高亮，便于识别
- **键盘导航**：支持快捷键导航和选择

## 编译版本

| 版本 | 状态 | 构建系统 | 发布日期 |
|------|------|---------|----------|
| 3.2 | built | autotools | 2026-05-22 |

## 依赖

- ncursesw（静态链接）
- readline
- libm

## 安装

通过 cmd-pkgs 公共安装脚本部署：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- hstr 3.2
```

## 使用方法

```bash
# 查看版本
hstr --version

# 作为别名使用（hh）
hh

# 在 shell 配置中绑定快捷键
bind '"\C-r": "\C-a hstr -- \C-j"'
```

## 项目信息

- **主页**: https://github.com/dvorka/hstr
- **许可证**: Apache-2.0
- **作者**: Martin Dvorak

## 平台适配说明

### OpenHarmony 适配补丁

1. **configure.ac**: 禁用 PKG_CHECK_MODULES 宏（平台无完整 pkg-config 支持）
2. **hstr.h**: 修复 ncursesw 头文件路径 + 添加缺失的 KEY_ 宏定义
3. **hstr_curses.h**: 修复 ncursesw 头文件路径
4. **Makefile.am**: 硬链接改为软链接（HMDFS 文件系统限制）

### 知识提取

- ncursesw 预编译包可能只提供 `curses.h`，不提供 `ncursesw/curses.h`
- curses.h 可能不包含扩展的 KEY_ 宏（KEY_END, KEY_DC, KEY_RESIZE 等）
- HMDFS 文件系统不支持硬链接，必须使用软链接替代