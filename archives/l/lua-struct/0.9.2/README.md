# lua-struct 0.9.2

## 软件简介

lua-struct 提供 Lua 的二进制数据打包/解包功能，类似 PHP 的 pack/unpack 函数。

- **主页**: https://github.com/iryont/lua-struct
- **版本**: 0.9.2
- **构建系统**: custom（纯 Lua）
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

lua-struct 是纯 Lua 库，无需编译步骤，仅需安装 .lua 文件。

### 创建的构建文件

创建 Makefile 处理安装流程（无补丁，仅新增构建文件）

## 依赖

- **必需**: lua/5.4.7

## 使用说明

```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;;"
```

```lua
local struct = require("struct")
-- 打包数据
local packed = struct.pack("<IhB", 12345, -3200, 255)
-- 解包数据
local I, h, B = struct.unpack("<IhB", packed)
```

## 支持的数据类型

- b/B: signed/unsigned byte
- h/H: signed/unsigned short
- i/I: signed/unsigned int
- l/L: signed/unsigned long
- f/d: float/double
- s: string
- cn: fixed-length string

## 编译产物

- `share/lua/5.4/struct.lua` (20KB)

## 编译日期

2026-06-10

## 质量门禁

- G1-G4 全部通过
- 功能验证: ✅ 通过