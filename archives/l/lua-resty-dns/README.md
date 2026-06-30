# lua-resty-dns

## 简介

lua-resty-dns 是一个基于 OpenResty 的 DNS 客户端库，提供非阻塞的 DNS 解析功能。它允许在 Nginx/OpenResty 环境中进行高性能的 DNS 查询操作。

## 功能概述

- 鷥阻塞 DNS 解析（基于 ngx_lua cosocket）
- 支持 A、AAAA、CNAME、MX、NS、SRV、TXT 等多种 DNS 记录类型
- 支持自定义 DNS 服务器
- 支持 DNS 缓存
- 支持超时设置

## OHOS 适配

- lua-resty-dns 是纯 Lua 库，无需编译
- 安装时需要设置正确的 `LUA_VERSION`（如 5.4）
- 需要依赖 OpenResty 或 ngx_lua 环境
- 无平台特定代码，跨平台兼容

## 依赖关系

- **运行依赖**: OpenResty 或 ngx_lua 环境
- **Lua 版本**: 5.1、5.3、5.4 或 LuaJIT 2.1

## 参考资料

- 官网: https://openresty.org/
- 源码: https://github.com/openresty/lua-resty-dns