# lua-jsonschema

JSON Schema data validator for Lua/LuaJIT.

## Description

This module is a data validator that implements JSON Schema drafts 4, 6, and 7.
Given a JSON schema, it will generate a validator function that can be used
to validate any kind of data (not limited to JSON).

Based on https://github.com/jdesgats/ljsonschema.

## Homepage

https://github.com/api7/jsonschema

## License

Apache License 2.0

## Installation

This is a pure Lua library. After extracting the precompiled package to `~/usr/local`,
set LUA_PATH to include the library path:

```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
```

Then you can use it in Lua:

```lua
local jsonschema = require('jsonschema')
local validator = jsonschema.generate_validator({type = "string"})
local ok, err = validator("hello")
```

## Dependencies

- net-url
- lrexlib-pcre (optional, for regex pattern matching)

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.9.13 | built | Latest version |