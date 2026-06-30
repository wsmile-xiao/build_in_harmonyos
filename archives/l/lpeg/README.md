# lpeg

LPeg 是 Lua 的解析表达式语法（PEG）模式匹配库，提供比 Lua 内置模式匹配更强大的功能。

## 描述

LPeg 实现了 PEG（Parsing Expression Grammars），这是一种识别性的文法，比传统的正则表达式更强大、更易读。

## 版本

- 1.1.0 (最新稳定版)

## 依赖

- lua >= 5.1

## 构建系统

简单 Makefile，需要手动指定编译器和 Lua 头文件路径。

## OHOS 适配

- 编译器：clang（原 Makefile 使用 gcc）
- LUADIR：指向 `~/usr/local/include/`

## 安装位置

- 模块路径：`lib/lua/5.4/lpeg.so`

## 使用示例

```lua
local lpeg = require("lpeg")

-- 简单匹配
local pattern = lpeg.P("hello")
print(pattern:match("hello world"))  -- 输出: 6

-- 组合模式
local digit = lpeg.R("09")
local number = digit^1
print(number:match("123abc"))  -- 输出: 4
```

## 补丁

- `0001-makefile.patch`: 适配 OpenHarmony 工具链（gcc→clang, LUADIR路径）

## 许可证

MIT License

## 官网

https://www.inf.puc-rio.br/~roberto/lpeg/