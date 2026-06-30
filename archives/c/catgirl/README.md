# catgirl

catgirl 是一个 C 语言编写 IRC 客户端，设计目标是简洁和高效。

## 基本信息

- **官网**: https://git.causal.agency/catgirl/about/
- **源码**: https://git.causal.agency/catgirl/snapshot/
- **分类**: networking

## 功能特性

- 简洁的用户界面
- TLS 加密支持
- 配置文件驱动
- 多服务器支持

## 编译版本

- **2.2a** (2026-05-22): 首次编译，静态链接

## 依赖

- ncurses (终端显示)
- libtls (TLS加密，来自 LibreSSL/LibreTLS)

## 已知问题

- configure 脚本需要手动修改 config.mk（HarmonyOS uname != "Linux"）
- musl libc 缺少 explicit_bzero（使用 __builtin_memset 替代）
