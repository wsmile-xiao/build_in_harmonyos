# lua-toml

## 描述
lua-toml 是一个 TOML 0.4.0 规范兼容的 Lua 库，用于解析和编码 TOML 格式的数据。

- 将 TOML 字符串序列化为 Lua 表
- 将 Lua 表序列化为 TOML 字符串
- 支持 strict 模式和 lua-friendly 模式

## 项目信息
- **上游**: https://github.com/jonstoler/lua-toml
- **版本**: 1.0
- **许可证**: The Happy License
- **依赖**: lua >= 5.2

## 构建系统
- **类型**: pure Lua library (builtin)
- **构建工具**: 无（纯 Lua 文件）
- **安装方式**: 复制 toml.lua 到 Lua 模块路径

## 已编译版本
- **1.0** (2026-06-09): 首次编译，纯 Lua 库

## 安装
预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-toml 1.0
```

安装后使用：
```lua
local TOML = require "toml"
local data = TOML.parse("key = \"value\"")
print(data.key)  -- 输出: value

local encoded = TOML.encode({key = "value"})
print(encoded)  -- 输出: key = "value"
```

## 注意事项
- 纯 Lua 库，无需编译步骤
- 安装路径：`$PREFIX/share/lua/5.4/toml.lua`
- 测试需要 busted 框架（本次编译跳过测试）
- Lua 版本：5.4.7