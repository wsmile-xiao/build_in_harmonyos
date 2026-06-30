# lua-redis

## 软件描述

lua-redis（redis-lua）是一个纯 Lua 客户端库，用于连接 Redis key-value 数据库。

## 主要特性

- 支持 Redis >= 1.2
- 命令管道化（pipelining）
- Redis 事务（MULTI/EXEC）with CAS
- 用户自定义命令
- UNIX domain sockets（LuaSocket 支持时）

## 依赖

- Lua >= 5.1
- LuaSocket

## 版本历史

| 版本 | 日期 | 状态 |
|------|------|------|
| 2.0.4 | 2012-07-15 | published |

## 链接

- GitHub: https://github.com/nrk/redis-lua
- License: MIT/X11