# zimfw 1.20.0 适配笔记

## 软件概述

zimfw（Zim Framework）是一个 Zsh 插件管理器，纯 Zsh 脚本实现，无需编译。
源码以单个 gzip 压缩的 .zsh 脚本文件分发（zimfw.zsh.gz）。

## 构建系统

- **类型**: custom（纯 Zsh 脚本，无编译）
- **安装方式**: 解压 .zsh.gz 得到 zimfw.zsh，复制到 share/ 目录
- **依赖**: 无（仅需 zsh 运行时）

## 适配说明

- zimfw 是纯 Zsh 脚本，conanfile.py 的 `build()` 下载并解压 .zsh.gz 文件
- `package()` 将 zimfw.zsh 复制到 share/ 目录
- `settings` 仅需 `os` 和 `arch`（无编译器相关设置）
- `package_type` 为 `application`（命令行工具）
- 无补丁、无依赖
- 源码 URL 为 GitHub releases，SHA256 已验证

## 测试

- 上游无独立测试套件
- test_package 使用烟雾测试：验证 zimfw.zsh 文件存在且 zsh 语法检查通过
- 注意：系统 zsh 5.9 缺少 is-at-least 自动加载函数，无法直接运行 zimfw --version
- test_package 使用 `zsh -n` 语法检查作为替代验证

## 已知问题

- OHOS 系统 zsh 5.9 (aarch64-unknown-linux-musl) 缺少 `is-at-least` 等自动加载函数
- init-build 无法处理 .zsh.gz 格式（仅支持 tar.gz/tar.xz/tar.bz2/zip）
- 需手动创建归档骨架
---

**编译结束**: 2026-07-17 11:13
**最终状态**: built
