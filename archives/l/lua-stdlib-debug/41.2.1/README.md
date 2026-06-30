# lua-stdlib-debug 41.2.1

## 软件简介

lua-stdlib-debug 是 lua-stdlib 的调试增强模块，提供 std.debug 子模块。

- **主页**: https://github.com/lua-stdlib/lua-stdlib
- **版本**: 41.2.1
- **构建系统**: autotools
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

使用 lua-stdlib 41.2.1 源码编译，提供独立的 std.debug 模块归档。

### 关键问题

1. **Lua 版本兼容**: 修改版本上限从 5.4 到 5.5
2. **HMDFS umask 权限**: 修改 configure 的 umask 设置

### 补丁文件

- `0001-configure.patch`: Lua 版本上限 + umask 修复

## 依赖

- **必需**: lua/5.4.7

## 使用说明

```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;/storage/Users/currentUser/usr/local/share/lua/5.4/?/init.lua;;"
```

```lua
require("std.debug")
-- 使用调试增强功能
```

## 编译产物

- `share/lua/5.4/std/debug.lua` (28KB)
- `share/lua/5.4/std/debug_init/init.lua` (860B)

## 编译日期

2026-06-10

## 质量门禁

- G1-G4 全部通过
- 功能验证: ✅ 通过