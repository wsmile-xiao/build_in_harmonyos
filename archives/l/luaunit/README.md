# luaunit

LuaUnit is a popular unit-testing framework for Lua, with an interface typical of xUnit libraries (Python unittest, Junit, NUnit, ...). It supports several output formats (Text, TAP, JUnit, ...) to be used directly or work with Continuous Integration platforms (Jenkins, Hudson, ...).

## Description

- **Category**: Testing
- **License**: BSD
- **Homepage**: https://github.com/bluebird75/luaunit

## Features

- xUnit-style interface for Lua unit testing
- Multiple output formats: Text, TAP, JUnit
- Works with CI platforms (Jenkins, Hudson, etc.)
- Single-file library with no external dependencies
- Comprehensive assertion library
- Pretty stringifier for complex tables
- Scientific computing support (assertAlmostEquals, etc.)

## Dependencies

- Lua >= 5.1

## Installation

luaunit is a pure Lua library and does not require compilation. Simply copy `luaunit.lua` to your Lua library directory:

```
/usr/local/share/lua/5.4/luaunit.lua
```

For OpenHarmony systems with Lua compiled with --prefix=/usr/local, you may need to set LUA_PATH:

```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
```

## Usage

```lua
local lu = require('luaunit')

function TestMyModule:testAdd()
    lu.assertEquals(2 + 2, 4)
end

os.exit(lu.LuaUnit.run())
```

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 3.5 | published | 2026-06-09 | Pure Lua library, no compilation required |

## Verification

```bash
lua -e "local lu = require('luaunit'); print('LuaUnit version:', lu.VERSION)"
# Output: LuaUnit version: 3.5
```

## References

- Documentation: http://luaunit.readthedocs.org/en/latest/
- GitHub: https://github.com/bluebird75/luaunit
- LuaRocks: https://luarocks.org/modules/bluebird75/luaunit