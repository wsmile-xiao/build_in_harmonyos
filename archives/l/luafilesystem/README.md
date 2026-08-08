# luafilesystem

## Overview

LuaFileSystem is a Lua C module that exposes portable file-system attributes,
directory iteration, and current-directory helpers. It is needed by Penlight
modules such as `pl.dir`, which are used by Busted.

This package provides the LuaRocks release `1.8.0-1` for the nvim-lspconfig
Path B dependency chain.

## Package Layout

- Native Lua module: `$PREFIX/lib/lua/5.4/lfs.so`
- License: `$PREFIX/licenses/LICENSE`

## Usage

Set `LUA_CPATH` to include the installed native module path:

```sh
export LUA_CPATH="$PREFIX/lib/lua/5.4/?.so;;"
```

Then load the module from Lua:

```lua
local lfs = require("lfs")
print(lfs.currentdir())
```

## License

MIT/X11

