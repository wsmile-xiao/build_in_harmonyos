# dkjson

## Overview

dkjson is David Kolf's pure Lua JSON encoder and decoder for Lua 5.1 through
Lua 5.4. This package provides the LuaRocks release `2.8-1` for the
nvim-lspconfig Path B dependency chain.

## Package Layout

- Lua module: `$PREFIX/share/lua/5.4/dkjson.lua`
- License/readme: `$PREFIX/licenses/readme.txt`

## Usage

Set `LUA_PATH` to include the installed Lua module path:

```sh
export LUA_PATH="$PREFIX/share/lua/5.4/?.lua;$PREFIX/share/lua/5.4/?/init.lua;;"
```

Then load the module from Lua:

```lua
local json = require("dkjson")
local encoded = json.encode({hello = "OHOS"})
local decoded = json.decode(encoded)
```

## License

MIT/X11

