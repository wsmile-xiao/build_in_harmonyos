# luassert

Lua 断言扩展库，提供丰富的断言功能，支持自定义断言和修饰符。

## 描述

luassert 扩展了 Lua 的内置断言，提供额外的测试和创建自定义断言的能力。可以使用 `not` 修饰断言链。

## 版本

- 1.9.0 (最新稳定版)

## 依赖

- lua >= 5.1
- say >= 1.4.0

## 构建系统

纯 Lua 库，使用 LuaRocks builtin 构建类型。

## 安装位置

- 模块路径：`/usr/local/share/lua/5.4/luassert/`

## 使用示例

```lua
local assert = require("luassert")

assert.True(true)
assert.is.True(true)
assert.is_true(true)
assert.is_not.True(false)
assert.are.equal(1, 1)
assert.has.errors(function() error("this should fail") end)
```

## 许可证

MIT License
