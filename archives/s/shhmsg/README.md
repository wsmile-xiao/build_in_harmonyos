# shhmsg

shhmsg 是一个面向终端程序的轻量级 C 消息输出库，提供统一的错误、普通消息和分级详细信息输出接口。

## 功能概述

- 设置并提取程序名，用于生成一致的诊断前缀。
- 支持普通消息、错误消息、`errno` 消息和致命错误消息。
- 支持 quiet 模式和可配置的 verbose 级别。
- 可分别重定向错误、普通消息和 verbose 消息的输出流。

## OHOS 适配

- 使用 HarmonyOS PC aarch64 原生 Clang 和上游 Makefile 构建。
- 源码仅依赖标准 C 库，在 HarmonyOS musl 环境无需源码补丁。
- 动态包使用实体 SONAME 别名，避免依赖 HMDFS 软链接行为。
- 消费者测试覆盖主要消息 API，并独立验证 OHOS/aarch64 平台宏与 LP64 ABI。

## 依赖关系

- 编译依赖：Make、Clang。
- 运行依赖：HarmonyOS libc。
- 第三方依赖：无。

## 参考资料

- 上游主页：https://shh.thathost.com/pub-unix/
- 上游源码：https://shh.thathost.com/pub-unix/files/shhmsg-1.4.2.tar.gz
