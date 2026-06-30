# turbo

Turbo.lua 是一个高性能的网络框架，基于 LuaJIT 2。

## 简介

Turbo.lua 是一个使用 LuaJIT 2 编写的高性能、事件驱动、非阻塞 I/O 框架，类似于 Node.js 和 Tornado。它旨在为 Lua 提供现代化的网络编程能力。

## 特性

- 基于 LuaJIT 2 的高性能执行
- 非阻塞 I/O 和事件驱动架构
- 内置 HTTP 服务器和客户端
- WebSocket 支持
- SSL/TLS 支持（通过 OpenSSL）
- 轻量级和快速响应

## 编译信息

- **版本**: 2.1.2
- **构建系统**: Makefile
- **依赖**: LuaJIT 2, OpenSSL
- **编译日期**: 2026-06-09

## 使用说明

Turbo 需要 LuaJIT 2 运行环境。安装后可通过 LuaJIT 运行 Turbo 应用：

```lua
local turbo = require "turbo"
turbo.run_app(turbo.app:new())
```

## 相关链接

- 官网: https://turbo.lua.org
- GitHub: https://github.com/kernelsauce/turbo