# lua-lsqlite3

Lua 的 SQLite3 数据库绑定，提供完整的 SQLite3 功能访问。

## 描述

lua-lsqlite3 提供两种版本：
- `lsqlite3.so`: 动态链接外部 sqlite3 库
- `lsqlite3complete.so`: 内嵌 sqlite3 3.24.0

## 版本

- 0.9.4 (最新版本)

## 依赖

- lua >= 5.1
- sqlite3 >= 3.0

## 构建系统

原始 Makefile 依赖 luarocks，需要手动创建 `Makefile.ohos`。

## OHOS 适配注意事项

⚠️ **平台限制**：OpenHarmony Lua 不支持动态加载模块（缺少 libdl 库）

解决方案：
- 使用静态库 `liblsqlite3complete.a` 链接到自定义 Lua 解释器
- 或重新编译 Lua 启用 `-DLUA_USE_DLOPEN`（需要 libdl）

## 安装位置

- 动态模块：`lib/lua/5.4/lsqlite3.so`
- 静态库：`lib/liblsqlite3complete.a`
- 外部依赖：`lib/external/libsqlite3.so.0`

## 使用示例

```lua
local sqlite3 = require("lsqlite3")

local db = sqlite3.open("test.db")
db:exec("CREATE TABLE test(id INTEGER, name TEXT)")
db:exec("INSERT INTO test VALUES(1, 'hello')")

for row in db:nrows("SELECT * FROM test") do
    print(row.id, row.name)
end

db:close()
```

## 许可证

MIT License

## 官网

https://github.com/slanska/lsqlite3