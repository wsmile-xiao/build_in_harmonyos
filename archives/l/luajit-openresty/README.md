# LuaJIT (OpenResty Branch)

## 简介

LuaJIT 是一个高效 的 Lua 解释器，使用即时编译(JIT)技术将 Lua 代码编译为优化的机器码。OpenResty 的 LuaJIT 分支包含额外的优化和功能，专为高性能 Web 应用设计。

## 主要特性

- **高性能**: JIT 编译器提供接近 C 语言的执行速度
- **FFI 支持**: 直接调用 C 函数，无需绑定
- **OpenResty 优化**: 针对 OpenResty 应用场景的额外功能
- **跨平台**: 支持多种 CPU 架构

## 已编译版本

| 版本 | 状态 | 架构 | 编译日期 |
|------|------|------|---------|
| 2.1-20260311 | ✅ published | aarch64 | 2026-05-19 |

## 使用方法

### 安装预编译包

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- luajit-openresty 2.1-20260311
```

### 基本使用

```bash
# 查看版本
luajit -v

# 执行 Lua 代码
luajit -e "print('Hello, World!')"

# 运行 Lua 脚本
luajit script.lua

# 交互模式
luajit -i
```

### FFI 示例

```lua
local ffi = require("ffi")
ffi.cdef[[
    int printf(const char *fmt, ...);
]]
ffi.C.printf("Hello from FFI!\n")
```

## 构建信息

- **构建系统**: 自定义 Makefile
- **编译器**: clang 15.0.4
- **目标平台**: 鸿蒙 aarch64-linux
- **安装前缀**: /usr/local

## 依赖关系

无外部依赖，LuaJIT 是自包含的。

## 相关链接

- [LuaJIT 官网](https://luajit.org/)
- [OpenResty LuaJIT GitHub](https://github.com/openresty/luajit2)
- [LuaJIT FFI 文档](https://luajit.org/ffi.html)

## 许可证

MIT License - Copyright (C) 2005-2026 Mike Pall
