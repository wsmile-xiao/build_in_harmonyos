# lub

**Display Name**: Lub (Lua Utility Belt)

**Description**: A collection of utility modules for Lua programming, providing common operations like directory handling, parameter parsing, and template processing.

**Homepage**: https://github.com/lubyk/lub

**License**: MIT

## Category

lua-library

## Build System

cmake

## Dependencies

- lua >= 5.1, < 5.4
- luafilesystem >= 1.8.0 (可选，用于 lub.Dir 功能)

## Modules Provided

- `lub.Autoload` - Automatic module loading
- `lub.Dir` - Directory operations (需要 luafilesystem)
- `lub.init` - Initialization utilities
- `lub.Param` - Parameter parsing
- `lub.Template` - Template processing

## Install Location

- `~/usr/local/share/lua/5.4/lub/`

## Usage Example

```lua
local lub = require('lub')
lub.Dir.list('.')  -- 需要安装 luafilesystem
local param = lub.Param {name = 'value'}
```

## OHOS Adaptation Notes

- 纯 Lua 库，无二进制编译
- 源码来源：LuaRocks src.rock 文件（非标准 tarball）
- 需要修改 CMakeLists.txt 的 cmake_minimum_required VERSION
- 完整功能需要先编译 luafilesystem

## Source

- LuaRocks: https://luarocks.org/modules/gaspard/lub
- GitHub: https://github.com/lubyk/lub