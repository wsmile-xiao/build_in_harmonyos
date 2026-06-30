# lua-microlight

A compact set of Lua utility functions.

## Description

Microlight provides a table stringifier, string split and substitution,
useful table operations, basic class support and some functional helpers.

This is a pure Lua library with no native code compilation required.

## Installation

The module `ml` will be installed to:
- `share/lua/5.4/ml.lua`

To use the module, set LUA_PATH:
```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
lua -e "local ml = require('ml')"
```

## Dependencies

- lua >= 5.1

## Usage Example

```lua
local ml = require('ml')

-- String split
local parts = ml.split("hello world test")
print(parts[1]) -- "hello"

-- File exists
print(ml.exists("README.md")) -- returns path or nil
```

## License

MIT/X11

## Homepage

http://stevedonovan.github.com/microlight/

## Version

1.0 (from LuaRocks rockspec microlight-1.0-1.rockspec)
