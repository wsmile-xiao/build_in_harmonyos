# lua-rapidjson

## 简介
lua-rapidjson 是一个基于 RapidJSON 的 Lua JSON 库，提供高性能的 JSON 编码和解码功能。

## OHOS 适配
- 需要 Lua 5.1+ 或 LuaJIT 运行时
- CMake 构建时需指定 LUA_INCLUDE_DIR 和 LUA_LIBRARIES
- 编译产物为 rapidjson.so 动态库

## 依赖
- lua >= 5.1
- RapidJSON（内嵌）

## 功能验证
```lua
local rapidjson = require('rapidjson')
local data = rapidjson.decode('{"key":"value"}')
print(data.key)  -- 输出: value
```

## 参考
- GitHub: https://github.com/xpol/lua-rapidjson
