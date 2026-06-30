# lua-pgmoon

## 简介
lua-pgmoon 是一个 PostgreSQL 客户端库，为 Lua 和 OpenResty 提供 PostgreSQL 数据库连接和查询功能。

## OHOS 适配
- 纯 Lua 实现，无需编译
- 支持 OpenResty cosocket API（异步查询）
- 支持 LuaSocket/cqueues（普通 Lua 环境）

## 依赖
- lua >= 5.1
- lpeg（解析复杂类型）

## 功能验证
```lua
local pgmoon = require("pgmoon")
local pg = pgmoon.new({host="localhost", user="test", database="testdb"})
pg:connect()
local res = pg:query("SELECT * FROM users")
pg:disconnect()
```

## 参考
- GitHub: https://github.com/Kong/pgmoon
