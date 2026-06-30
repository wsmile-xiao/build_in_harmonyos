# lua-stacktraceplus 0.1.2

## 软件简介

StackTracePlus 是 Lua 的增强堆栈跟踪库，提供更详细的错误调试信息。

- **主页**: https://github.com/ignacio/StackTracePlus
- **版本**: 0.1.2
- **构建系统**: builtin（纯 Lua）
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

StackTracePlus 是纯 Lua 模块，无需编译，仅需安装 .lua 文件。

### Lua 版本兼容性

官方要求: lua >= 5.1, < 5.4
实际测试: 在 Lua 5.4.7 上可正常工作

## 依赖

- **必需**: lua/5.4.7

## 使用说明

```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;;"
```

```lua
local stp = require("StackTracePlus")
debug.traceback = stp.stacktrace
-- 现在错误信息更详细
```

## 编译产物

- `share/lua/5.4/StackTracePlus.lua`

## 编译日期

2026-06-10

## 质量门禁

- G1-G3 通过（纯 Lua 库无二进制）
- G4 有警告（缺少部分字段，已修复）
- 功能验证: ✅ 通过