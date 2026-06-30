# luasql 2.3.5 (lua-sql)

## 软件简介

LuaSQL 是 Lua 的数据库访问库，支持多种数据库驱动（MySQL、PostgreSQL、SQLite、Oracle、ODBC 等）。

- **主页**: https://github.com/lunarmodules/luasql
- **版本**: 2.3.5
- **构建系统**: Makefile
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

1. **关键发现**: OpenHarmony Lua 扩展模块需要显式链接 `-llua`（不能依赖主程序导出符号）
2. 修改 config 文件适配编译环境
3. 手动安装到 staging 目录（不支持 DESTDIR）

### 主要修改

补丁文件 `0001-config.patch`:
- 设置 PREFIX 和 Lua 版本
- **添加 `-llua -lm` 到 LIB_OPTION**（关键修复）

## 依赖

- **必需**: lua/5.4.7, sqlite3

## 使用说明

```lua
local luasql = require("luasql.sqlite3")
local env = luasql.sqlite3()
local conn = env:connect("/path/to/database.db")
```

## 编译产物

- `lib/lua/5.4/luasql/sqlite3.so` - SQLite3 驱动（34KB）

## 关键知识沉淀

OpenHarmony 平台 Lua 扩展模块编译需显式链接 Lua 库，这是与 Linux 平台的关键差异。

## 编译日期

2026-06-10

## 质量门禁

- G1-G4 全部通过
- 功能验证: ✅ 完整数据库操作测试通过