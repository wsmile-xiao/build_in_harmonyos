# rcm

## 简介
rcm 是 thoughtbot 开发的 dotfile 管理工具套件，用于管理 Unix 系统下的 rc 文件（dotfiles）。它提供四个命令行工具，通过符号链接的方式将 dotfiles 目录中的文件链接到用户主目录，支持标签（tags）、主机专属文件（host-specific）、排除规则等高级功能。

## 命令
- **rcup** — 安装和更新 dotfiles，创建符号链接到主目录
- **rcdn** — 移除 dotfiles 符号链接（rcup 的逆操作）
- **mkrc** — 将现有 dotfile 引入到 dotfiles 目录
- **lsrc** — 列出所有 dotfiles 及其符号链接目标

## OHOS 适配
- **构建系统**: 使用 autotools（configure + make），release tarball 已预生成 configure 和 man 页
- **shebang 修复 (E165)**: configure 脚本使用 `#! /bin/sh`，OHOS 无 /bin/sh，替换为 `#!/system/bin/sh`；bin/*.in 脚本（lsrc/mkrc/rcdn/rcup）均使用 `#!@SHELL@`，替换为 `#!/data/service/hnp/bin/bash`
- **umask 修复 (E110)**: configure 中 `umask 077` 在 HMDFS 上导致临时目录权限问题，替换为 `umask 002`
- **无平台检测**: configure.ac 无 AC_CANONICAL_HOST，不需要 config.guess/config.sub，无需 E007 修复
- **预生成文件**: Release tarball 已包含预生成的 configure、Makefile.in、man 页，无需 autoreconf 或 ruby-mustache

## 依赖
- 构建工具: autotools
- 运行时: bash（OHOS 使用 /data/service/hnp/bin/bash）
- 无编译依赖（纯 shell 脚本工具，arch=noarch）

## 安装产物
- bin/lsrc — 列出 dotfiles 符号链接
- bin/mkrc — 将 dotfile 引入 dotfiles 目录
- bin/rcup — 安装/更新 dotfiles
- bin/rcdn — 卸载 dotfiles
- share/rcm/rcm.sh — 共享库脚本
- share/man/man1/ — man 手册页

## 功能验证
```bash
lsrc
mkrc .vimrc
rcup
rcdn
```

## 参考
- GitHub: https://github.com/thoughtbot/rcm
- 教程: https://thoughtbot.github.io/rcm/rcm.7.html
