# Teal

Teal is a typed dialect of Lua. It adds optional type annotations to Lua code, providing static type checking while maintaining full compatibility with Lua's runtime semantics.

## Key Features

- Optional type annotations
- Static type checking
- Full Lua compatibility (works with Lua 5.1-5.4 and LuaJIT)
- Zero dependencies for core compiler (tl.lua)
- MIT license

## Installation

Teal can be installed via LuaRocks:
```
luarocks install tl
```

Or by directly using the `tl.lua` file.

## Usage

- `tl run script.tl` - run a Teal script
- `tl check module.tl` - type check a Teal module
- `tl gen module.tl` - generate Lua code from Teal

## Homepage

https://github.com/teal-language/tl