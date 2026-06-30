# lua-sqlite 2.6.0

## 软件简介

lua-sqlite 提供对 SQLite 数据库的 Lua 绑定，是 LuaSQL 项目的一部分。

- **主页**: https://github.com/lunarmodules/luasql
- **版本**: 2.6.0
- **构建系统**: Makefile
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

1. 修改 Makefile 添加 Lua 库链接（`LIBS=-llua`）
2. 修改 config 文件适配编译环境
3. Lua 5.4 版本适配

### 补丁文件

- `0001-Makefile.patch`: 添加 Lua 库链接
- `0002-config.patch`: PREFIX、LUA_SYS_VER、路径配置

## 依赖

- **必需**: lua/5.4.7, sqlite3

## 使用说明

```lua
local sql = require("luasql.sqlite3")
local env = sql.sqlite3()
local conn = env:connect("/path/to/database.db")
```

## 编译产物

- `lib/lua/5.4/luasql/sqlite3.so` (35KB)

## 编译日期

2026-06-10

## 质量门禁

- G1-G3 通过
- G4 有警告（manifest 字段问题，非关键）
- 功能验证: ✅ 通过