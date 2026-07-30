# lua-pty

## 简介
lua-pty 是一个 Lua PTY（伪终端）绑定库，提供 forkpty、openpty 等 Linux PTY 函数的 Lua 接口。

## OHOS 适配
- C 模块需要编译
- 需要 Lua 静态库（-fPIC 编译）用于链接到共享库
- 编译产物 core.so 需要 ELF 签名
- License: GPL-3.0

## 依赖
- lua >= 5.1
- libutil（系统库）

## 功能验证
```lua
local pty = require("pty")
local pid, master_fd = pty.forkpty()
```

## 参考
- GitHub: https://github.com/arcapos/lua-pty
