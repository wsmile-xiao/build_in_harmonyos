# lua-resty-core

## 简介

lua-resty-core 是 OpenResty 的核心 Lua 库，使用 LuaJIT FFI 重新实现了 ngx_lua 模块的 Nginx API for Lua。相比基于 Lua C API 的默认实现，FFI 实现更快、更安全、更完整。

## 特性

- 纯 Lua 库，无编译步骤
- 基于 LuaJIT FFI 实现
- 支持 Lua 5.1/5.4 和 LuaJIT
- 需要 OpenResty 环境才能运行

## 安装

lua-resty-core 会在 OpenResty 启动时自动加载。安装后文件位于：
- `{PREFIX}/lib/lua/{LUA_VERSION}/resty/`
- `{PREFIX}/lib/lua/{LUA_VERSION}/ngx/`

## 依赖

- Lua 5.4 或 LuaJIT
- OpenResty（包含 ngx_lua 模块）

## 版本历史

- v0.1.27 (2026-06-11): built

## 许可证

BSD 2-Clause License
