# LuaSQL

SQLite3 driver for LuaSQL — database connectivity for Lua.

## Overview

LuaSQL is a Lua extension library that provides database connectivity.
This package builds the SQLite3 driver, which compiles to a shared
object (`sqlite3.so`) loaded by Lua at runtime via `require("luasql.sqlite3")`.

## Build System

- **System**: Makefile
- **Compiler**: clang
- **Dependencies**: lua/5.4.8, sqlite3/3.49.1

## OHOS Adaptation

- No patches needed — all paths passed via make variables
- Lua symbols resolved at runtime (not linked at compile time)
- SQLite3 statically linked into the .so
- .so installed to `lib/luasql/` for Lua `require` path compatibility

## Usage

```lua
local luasql = require("luasql.sqlite3")
local env = luasql.sqlite3()
local con = env:connect(":memory:")
con:execute("CREATE TABLE test (id INTEGER, name TEXT)")
con:execute("INSERT INTO test VALUES (1, 'hello')")
local cur = con:execute("SELECT * FROM test")
local row = cur:fetch({}, "a")
print(row.id, row.name)
cur:close()
con:close()
env:close()
```
