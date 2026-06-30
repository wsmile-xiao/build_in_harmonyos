# lua-resty-http

Lua HTTP client cosocket driver for OpenResty / ngx_lua.

## 描述

lua-resty-http 是一个基于 OpenResty cosocket API 的 HTTP 客户端库，提供高性能的 HTTP 请求功能。

## 特性

- 支持 HTTP/1.1 协议
- 基于 cosocket 的非阻塞 I/O
- SSL/TLS 支持
- 代理支持
- 连接池和连接复用
- 流式请求和响应处理

## 依赖

- Lua 5.1+ 或 LuaJIT 2.0+
- OpenResty 或 ngx_lua

## 安装

```bash
# 使用预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-resty-http 0.17.2

# 或手动安装
make PREFIX=/usr/local LUA_VERSION=5.4 install
```

## 版本历史

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.17.2 | published | 2026-06-11 | 当前版本 |

## 授权协议

BSD 2-clause license

## 官方链接

- GitHub: https://github.com/ledgetech/lua-resty-http