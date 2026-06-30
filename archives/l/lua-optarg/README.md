# lua-optarg

## 简介
lua-optarg 是一个简单的 Lua 命令行参数解析库。

## OHOS 适配
- 纯 Lua 实现，无需编译
- 安装到 Lua 模块路径即可使用

## 依赖
- lua >= 5.1

## 功能验证
```lua
local optarg = require("optarg")
local args = optarg.parse({"--input=file.txt", "--output=out.txt"})
print(args.input)  -- 输出: file.txt
```

## 参考
- GitHub: https://github.com/ncopa/lua-optarg
