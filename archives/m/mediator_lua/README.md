# mediator_lua

## Overview

mediator_lua is a pure Lua event mediator used by Busted. It lets callers
subscribe callbacks to channel namespaces and publish events through those
channels.

This package provides the LuaRocks release `1.1.2-0` for the nvim-lspconfig
Path B dependency chain.

## Package Layout

- Lua module: `$PREFIX/share/lua/5.4/mediator.lua`
- License/readme: `$PREFIX/licenses/README.md`

## Usage

Set `LUA_PATH` to include the installed Lua module path:

```sh
export LUA_PATH="$PREFIX/share/lua/5.4/?.lua;$PREFIX/share/lua/5.4/?/init.lua;;"
```

Then load the module from Lua:

```lua
local Mediator = require("mediator")
local mediator = Mediator()
mediator:subscribe({"events"}, function(payload) print(payload.message) end)
mediator:publish({"events"}, {message = "OHOS"})
```

## License

MIT

