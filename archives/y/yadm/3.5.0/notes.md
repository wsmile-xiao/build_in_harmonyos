# yadm 3.5.0 适配笔记

## 软件概述

yadm（Yet Another Dotfiles Manager）是一个基于 Git 的 dotfiles 管理工具，纯 bash 脚本实现，无需编译。

## 构建系统

- **类型**: makefile（纯脚本，无编译）
- **安装方式**: `make install PREFIX=xxx`，将 yadm 脚本复制到 bin 目录
- **依赖**: 无（仅需 bash 和 git）

## 适配说明

- yadm 是纯 bash 脚本，conanfile.py 的 `build()` 为空，`package()` 直接复制脚本文件
- `settings` 仅需 `os` 和 `arch`（无编译器相关设置）
- `package_type` 为 `application`（命令行工具）
- 无补丁、无依赖

## 测试

- 上游测试基于 pytest + docker，不适用于 Conan 测试环境
- test_package 使用烟雾测试：运行 `yadm --version` 验证可执行性

## 已知问题

- yadm 的 shebang 为 `#!/bin/sh`，在 OHOS 环境下可能需要 bash 来执行
- yadm 脚本内部会检测并 `exec bash`，前提是系统有 bash
