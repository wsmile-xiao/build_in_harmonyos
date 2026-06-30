# lua-stdlib 41.2.1

## 软件简介

lua-stdlib 是 Lua 的标准库扩展，提供丰富的数据结构、函数式编程、IO 操作等功能。

- **主页**: https://github.com/lua-stdlib/lua-stdlib
- **版本**: 41.2.1
- **构建系统**: autotools
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 关键问题与解决方案

1. **Lua 版本检测失败**
   - 问题: AX_PROG_LUA 使用开区间检查，Lua 5.4.7 不满足 `ver < 5.4`
   - 解决: 修改 configure.ac 版本上限从 5.4 到 5.5

2. **HMDFS SELinux 限制**
   - 问题: configure 的 `umask 077` 不允许创建临时文件
   - 解决: `sed -i 's/umask 077/umask 022/g' configure`

### 补丁文件

- `0001-INSTALL.patch` - autoreconf 自动生成
- `0002-Makefile.in.patch` - autoreconf 自动生成
- `0003-aclocal.m4.patch` - autoreconf 自动生成
- `0004-build-aux-install-sh.patch` - autoreconf 自动生成
- `0005-build-aux-missing.patch` - autoreconf 自动生成
- `0006-configure.patch` - Lua 5.4 支持 + HMDFS umask 修复
- `0007-configure.ac.patch` - **关键**: 支持 Lua 5.4

## 依赖

- **必需**: lua/5.4.7

## 使用说明

```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;/storage/Users/currentUser/usr/local/share/lua/5.4/?/init.lua;;"
```

```lua
local std = require("std")
-- 使用 std 库的各种功能
```

## 编译产物

- `share/lua/5.4/std.lua` - 主模块
- `share/lua/5.4/std/*.lua` - 17 个子模块

## 知识沉淀

新增知识图谱条目 E081: AX_PROG_LUA 版本范围不匹配导致 Lua 5.4 检测失败

## 编译日期

2026-06-10

## 质量门禁

- G1-G4 全部通过
- 功能验证: ✅ 通过