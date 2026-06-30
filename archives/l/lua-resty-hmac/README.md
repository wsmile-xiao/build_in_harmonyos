# lua-resty-hmac

OpenResty HMAC 加密库，提供基于 FFI 的 HMAC 算法实现。

## 描述

lua-resty-hmac 是 OpenResty 生态中的 HMAC 加密模块，支持多种哈希算法（SHA256、SHA512 等）。依赖 LuaJIT 的 FFI 功能，在 OpenResty 环境中运行。

## 版本

- v0.06 (2026-06-11)

## 依赖

- LuaJIT（FFI 模块）
- lua-resty-string
- OpenResty 环境

## 安装路径

`{PREFIX}/lib/lua/5.4/resty/hmac.lua`

## 运行要求

需要在 OpenResty/LuaJIT 环境中使用，标准 Lua 5.4 不支持 FFI。
