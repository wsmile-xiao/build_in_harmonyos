# luasql (LuaSQL)

## 软件简介

LuaSQL is a simple interface from Lua to a DBMS. It enables a Lua program to:
- Connect to a database
- Execute SQL commands
- Retrieve data through cursors

## 支持的数据库驱动

| Driver | Status | Notes |
|--------|--------|-------|
| SQLite3 | ✅ Built | In-memory and file-based databases |
| MySQL | ⏳ Not built | Requires libmysqlclient |
| PostgreSQL | ⏳ Not built | Requires libpq |
| ODBC | ⏳ Not built | Requires unixodbc |
| Oracle OCI8 | ⏳ Not built | Requires Oracle client |
| Firebird | ⏳ Not built | Requires libfbclient |

## 主页

- https://github.com/lunarmodules/luasql

## 使用说明

```lua
local luasql = require("luasql.sqlite3")
local env = luasql.sqlite3()
local conn = env:connect("/path/to/database.db")
local cur = conn:execute("SELECT * FROM users")
local row = cur:fetch({}, "a")
print(row.name, row.age)
```

## OpenHarmony 适配

### 关键适配点

1. **显式 Lua 链接**: OHOS 不支持主程序导出符号给 .so 模块使用，必须在编译时显式链接 `-llua`
2. **SQLite3 amalgamation**: SQLite3 的 configure 脚本在 OHOS 上失败，直接编译 amalgamation 源码
3. **Lua make linux**: Lua 的 `make linux` 目标在 HarmonyOS 上正常工作

### 构建产物

- `lib/lua/5.4/luasql/sqlite3.so` — SQLite3 驱动模块
- `bin/lua` — Lua 解释器（用于测试）
- `lib/liblua.a` — Lua 静态库
- `include/*.h` — Lua 头文件

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.4.0 | published | 2026-07-15 |
| 2.3.5 | built | 2026-06-10 |
