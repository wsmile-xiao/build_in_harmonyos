# lustache

**Display Name**: Lustache

**Description**: Mustache templating for Lua - a pure Lua implementation of the Mustache templating standard.

**Homepage**: http://olivinelabs.com/lustache/

**License**: MIT

## Category

lua-library

## Build System

custom (Makefile)

## Dependencies

- lua >= 5.1

## Install Location

- `~/usr/local/share/lua/5.4/lustache.lua`
- `~/usr/local/share/lua/5.4/lustache/*.lua`

## Usage Example

```lua
local lustache = require('lustache')
local template = 'Hello, {{name}}!'
local data = {name='World'}
print(lustache:render(template, data))  -- Output: Hello, World!
```

## Notes

This is a pure Lua library with no binary compilation required. Installation involves copying Lua source files to the appropriate Lua library directory.