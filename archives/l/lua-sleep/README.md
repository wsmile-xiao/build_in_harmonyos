# lua-sleep

Lua module that provides a millisecond-precision sleep function.

## Description

This is a bare-bones Lua module that exposes a millisecond-precision sleep function. It is useful for adding delays in Lua scripts.

## Versions

- **0.1** (v1.0.0-4 from squeek502/sleep) - Latest version

## Usage

```lua
local sleep = require('sleep')

-- sleep for 1 second (1000 milliseconds)
sleep(1000)
```

## Building on OpenHarmony

This module uses CMake build system. On OpenHarmony, the following modifications are required:

1. Update `cmake_minimum_required` to at least 3.5
2. Add HarmonyOS platform detection and link against Lua library
3. Use `-undefined dynamic_lookup` to allow dynamic symbol resolution

## Patches

- `0001-CMakeLists.txt.patch` - Update CMake configuration for HarmonyOS compatibility

## Dependencies

- Lua 5.4+

## Installation

The module is installed to `$DEFAULT_PREFIX/lib/lua/5.4/sleep.so`.

To use the module, set `LUA_CPATH` environment variable:
```bash
export LUA_CPATH="$HOME/usr/local/lib/lua/5.4/?.so;"
```

## License

Unlicense (Public Domain)