# libnghttp2

## 简介

libnghttp2 是一个 HTTP/2 协议的 C 语言实现库，提供 HPACK 压缩器/解压缩器功能。它是 nghttp2 工具集的核心组件，支持 HTTP/2 的帧处理、流控制和头部压缩。

## 功能概述

- HTTP/2 协议栈实现（帧解析、流控制、流量控制）
- HPACK 头部压缩/解压缩
- HTTP/2 客户端/服务器 API
- 资源优先级处理
- 流依赖管理

## OHOS 适配

### 构建系统选择

**推荐使用 CMake 构建**。Autotools 构建在 HMDFS 文件系统上会遇到 `config.status` 临时文件创建失败的问题（与 HMDFS 权限限制和 shell 环境相关）。

### 平台识别

需要替换 `config.guess` 和 `config.sub` 为支持 `aarch64-unknown-linux-ohos` 的版本。

### 已知问题

- Autotools `configure` 脚本会在当前目录创建临时文件（如 `confXXXXXX`），HMDFS 对此有限制
- 使用 CMake 可完全规避此问题

## 依赖关系

### 编译依赖
- CMake >= 3.0
- clang/clang++ 编译器

### 运行依赖
- musl libc

## 参考资料

- 官网: https://nghttp2.org
- 源码: https://github.com/nghttp2/nghttp2
- 文档: https://nghttp2.org/documentation/