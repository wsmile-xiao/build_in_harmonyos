# libmpack-lua

`libmpack-lua` 是 libmpack 的 Lua 原生绑定，提供 MsgPack 序列化、反序列化和 MsgPack-RPC 会话 API。

## HarmonyOS 版本

- `1.0.13`：Lua 5.1 原生模块，产物为 `lib/lua/5.1/mpack.so`

## 依赖

- `lua/5.1.5`
- `libmpack/1.0.5`

## 使用

```lua
local mpack = require("mpack")
local blob = mpack.pack({message = "hello"})
local value = mpack.unpack(blob)
```

运行时需要将模块目录加入 `LUA_CPATH`；Conan 包会通过 `runenv_info` 自动提供该路径。

## 验证

版本目录中的 Conan 测试会执行官方 `test.lua`，并通过真实 Lua consumer 验证 `mpack.so`。HarmonyOS 目标额外验证动态加载器、`luaopen_mpack` 导出符号和目标平台宏。
