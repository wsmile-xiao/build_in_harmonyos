# OpenSC

智能卡工具和中间件，提供 PKCS#11、PKCS#15 和 OpenPGP 框架支持。

## 简介

OpenSC 是一套开源的智能卡（Smart Card）工具和库，为应用程序提供统一的智能卡访问接口。它实现了 PKCS#11 API（供浏览器/邮件客户端等使用）、PKCS#15 文件结构框架，以及 OpenPGP 卡支持。

## 主要功能

- **pkcs11**: PKCS#11 模块，供 Firefox/Thunderbird 等应用访问智能卡
- **pkcs15-tool**: 查看/操作 PKCS#15 结构的命令行工具
- **opensc-tool**: 智能卡通用检测工具
- **opensc-explorer**: 交互式智能卡文件浏览器

## HarmonyOS 适配要点

1. opensc 的 config.guess 已原生识别 `aarch64-unknown-linux-ohos`，无需修改
2. 需 `--disable-notify` 禁用桌面通知（鸿蒙无 libnotify）
3. 无需任何补丁 — 所有 autotools 生成文件（Makefile/config.status/libtool）由 configure 自动产出

## 依赖

- openssl — 核心加密库
- pcsc-lite（可选）— 智能卡读卡器中间件
- libnotify（鸿蒙不可用，需禁用）

## 安装

```bash
# 使用预编译包安装
curl -fsSL install.sh | sh -s -- opensc 0.26.1-r0
```

## 参考

- GitHub：https://github.com/OpenSC/OpenSC
- Wiki：https://github.com/OpenSC/OpenSC/wiki