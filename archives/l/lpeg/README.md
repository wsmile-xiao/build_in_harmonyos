# LPeg

Parsing Expression Grammars for Lua.

LPeg is a pattern-matching library for Lua, based on Parsing Expression Grammars (PEGs). It offers a more powerful and expressive alternative to regular expressions and Lua's native string patterns.

- **Homepage**: https://www.inf.puc-rio.br/~roberto/lpeg/
- **License**: MIT
- **Build system**: Makefile

## Build

lpeg compiles to a shared library (`lpeg.so`) that is loaded by Lua at runtime via `require("lpeg")`. At compile time, it needs Lua headers.

Since Lua is not yet published as a Conan recipe on the OHOS platform, the conanfile.py downloads and builds Lua from source to obtain the necessary headers.

```bash
make linux CC=clang LUADIR=/path/to/lua/src/
```

## Test

```bash
LUA_CPATH="./?.so" LUA_PATH="./?.lua" lua test.lua
```
