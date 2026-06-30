# middleclass

A simple OOP library for Lua with class creation, inheritance, and mixins.

## Description

middleclass provides a lightweight object-oriented programming system for Lua.
It supports class creation, inheritance, method overriding, and mixins.

This is a pure Lua library with no native code compilation required.

## Installation

The module `middleclass` will be installed to:
- `share/lua/5.4/middleclass.lua`

To use the module, set LUA_PATH:
```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
lua -e "local class = require('middleclass')"
```

## Dependencies

- lua >= 5.1

## Usage Example

```lua
local class = require('middleclass')

local Animal = class('Animal')
function Animal:initialize(name)
    self.name = name
end
function Animal:speak()
    print('My name is ' .. self.name)
end

local Dog = class('Dog', Animal)
function Dog:speak()
    print('My name is ' .. self.name .. ' and I bark!')
end

local dog = Dog:new('Rex')
dog:speak()
```

## License

MIT

## Homepage

https://github.com/kikito/middleclass

## Version

4.1.1