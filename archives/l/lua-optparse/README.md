# lua-optparse

## 简介
lua-optparse 是一个 Lua 命令行参数解析库，提供类似 argparse 的参数解析功能。

## OHOS 适配
- 纯 Lua 实现，无需编译
- 安装到 Lua 模块路径即可使用

## 依赖
- lua >= 5.1

## 功能验证
```lua
local optparse = require("optparse")
local parser = optparse.new()
parser:add_option("--output", {dest = "output"})
local args = parser:parse({"--output=test.txt"})
print(args.output)  -- 输出: test.txt
```

## 参考
- GitHub: https://github.com/davidm/lua-optparse
