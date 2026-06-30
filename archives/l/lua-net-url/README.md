# lua-net-url

URL parsing and construction library for Lua.

## Description

lua-net-url provides functions for parsing and constructing URLs.
It handles URL components like scheme, host, path, query parameters, and fragments.

This is a pure Lua library with no native code compilation required.

## Installation

The module `net.url` will be installed to:
- `share/lua/5.4/net/url.lua`

To use the module, set LUA_PATH:
```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
lua -e "local url = require('net.url')"
```

## Dependencies

- lua >= 5.1

## Usage Example

```lua
local url = require('net.url')

-- Parse a URL
local parsed = url.parse('https://example.com/path?query=value#fragment')
print(parsed.scheme)    -- 'https'
print(parsed.host)      -- 'example.com'
print(parsed.path)      -- '/path'
print(parsed.query)     -- {query = 'value'}

-- Construct a URL
local u = url.construct({
    scheme = 'https',
    host = 'example.com',
    path = '/api',
    query = {key = 'value'}
})
print(u) -- 'https://example.com/api?key=value'
```

## License

MIT

## Homepage

https://github.com/golgote/net-url

## Version

0.1.0