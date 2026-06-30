# lua-stdlib-normalize 2.0.3

## 软件简介

lua-stdlib-normalize 提供 Lua 代码规范化功能，是 std.normalize 模块的独立封装。

- **主页**: https://github.com/lua-stdlib/normalize
- **版本**: 2.0.3
- **构建系统**: custom（无标准构建流程）
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

此软件为纯 Lua 库，无标准构建流程：
- 无 configure 脚本
- 无 make install 目标
- 手动复制 Lua 文件到正确位置

### 依赖处理

包含依赖 std._debug v1.0.1 在预编译包中

## 依赖

- **必需**: lua/5.4.7, std._debug/1.0.1

## 使用说明

```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;/storage/Users/currentUser/usr/local/share/lua/5.4/?/init.lua;;"
```

```lua
local n = require("std.normalize")
print("版本:", n.version)
-- 使用规范化功能
```

## 编译产物

- `share/lua/5.4/std/normalize/` (5个文件)
- `share/lua/5.4/std/_debug/` (2个文件，依赖)

## 编译日期

2026-06-10

## 质量门禁

- G1-G3 通过（纯 Lua 无二进制）
- 功能验证: ✅ 通过