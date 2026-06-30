# sentry-native

Sentry SDK for C, C++ and native applications.

- **官网**: https://sentry.io/
- **源码**: https://github.com/getsentry/sentry-native
- **License**: MIT
- **语言**: C/C++
- **构建系统**: cmake

## 描述

sentry-native 是 Sentry 的 C/C++ SDK，用于在原生应用中捕获和上报崩溃、错误事件和性能数据。支持多种崩溃后端（crashpad、inproc、breakpad）和 HTTP 传输方式（curl、winhttp）。

在 OpenHarmony 平台上，当前编译配置使用 **inproc** 后端（进程内崩溃捕获）和 **none** 传输（无 HTTP 上报，需用户自行实现传输），因为平台缺少 curl 开发库。

## 可用版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.13.3 | published | inproc 后端 + none 传输，无 curl |