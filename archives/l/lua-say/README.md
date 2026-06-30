# lua-say

## 简介

lua-say 是一个简单的 Lua 字符串键值存储库，主要用于国际化（i18n）或其他需要命名空间字符串的场景。

## 版本

- 1.3-1

## 特性

- 纯 Lua 库，无 C 代码
- 支持命名空间字符串管理
- 适用于国际化场景
- Lua 5.1+ 兼容

## 依赖

- lua >= 5.1

## 编译说明

### 构建系统

lua-say 是一个纯 Lua 库，使用 LuaRocks 的 builtin 构建类型。由于没有传统的 configure/make 构建系统，我们提供了一个简单的 Makefile 来安装 Lua 模块文件。

### 安装位置

- Lua 模块：`$PREFIX/share/lua/5.4/say/init.lua`

### 使用方法

```lua
local say = require("say")

say:set_namespace("en")
say:set('money', 'I have %s dollars')
print(say('money', 1000))  -- I have 1000 dollars

say:set_namespace("fr")
say:set('so_much_money', "Tant d'argent!")
print(say('so_much_money'))  -- Tant d'argent!
```

## 许可证

MIT License

## 相关链接

- 项目主页：http://olivinelabs.com/busted/
- GitHub：https://github.com/Olivine-Labs/say