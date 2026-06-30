# lua-uuid

lua-uuid 是一个纯 Lua 实现的 UUID 生成库。

## 简介

lua-uuid 提供在 Lua 中生成各种格式 UUID 的功能。这是一个纯 Lua 实现，不依赖外部 C 库，可以跨平台使用。

## 特性

- 纯 Lua 实现，无需编译
- 支持多种 UUID 格式（v1, v2, v4, v5）
- 跨平台兼容
- 简单易用的 API

## 编译信息

- **版本**: 1.0.0
- **构建系统**: manual（纯 Lua）
- **依赖**: 无
- **编译日期**: 2026-06-09

## 使用说明

安装后直接在 Lua 中加载：

```lua
local uuid = require "uuid"
print(uuid.v4())  -- 生成随机 UUID
```

**注意**: lua-uuid 1.0.0 版本的重大变更：需要显式设置 RNG（随机数生成器）：

```lua
local uuid = require "uuid"
uuid.seed()  -- 设置随机数种子
print(uuid.v4())
```

## 相关链接

- GitHub: https://github.com/Tieske/uuid
- LuaRocks: uuid