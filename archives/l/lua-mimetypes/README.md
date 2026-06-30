# lua-mimetypes

Lua library for MIME type detection based on file extensions and filenames.

## Description

lua-mimetypes provides a simple way to guess the MIME type of a file based on its extension or filename. It includes a comprehensive database of common MIME types and supports both standard file extensions and special filenames (like README, Makefile, etc.).

## Version

- **1.0** (2026-06-15) - Built for OpenHarmony

## Dependencies

- Lua 5.4

## Installation

The library is installed to `~/usr/local/share/lua/5.4/`. To use it, set the `LUA_PATH` environment variable:

```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;$HOME/usr/local/share/lua/5.4/?/init.lua"
```

Or set it before running Lua:

```bash
LUA_PATH="~/usr/local/share/lua/5.4/?.lua" lua -e "local mime = require('mimetypes'); print(mime.guess('file.jpg'))"
```

## Usage

```lua
local mimetypes = require('mimetypes')

-- Guess by extension
local type1 = mimetypes.guess('image.jpg')    -- returns "image/jpeg"
local type2 = mimetypes.guess('data.json')    -- returns "application/json"

-- Guess by filename
local type3 = mimetypes.guess('README')       -- returns "text/plain"
local type4 = mimetypes.guess('.gitignore')   -- returns "text/plain"

-- Get version
print(mimetypes.version)                      -- prints "1.1.0"
```

## Notes

- Pure Lua library, no compilation required
- Requires LUA_PATH to be set correctly
- Includes comprehensive MIME type database from Python's mimetypes module