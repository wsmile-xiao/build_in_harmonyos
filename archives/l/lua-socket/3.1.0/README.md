# lua-socket 3.1.0

## 软件简介

LuaSocket is a network support library for Lua, providing TCP/UDP sockets, HTTP client, FTP client, SMTP client, and MIME functionality.

- **Homepage**: https://github.com/lunarmodules/luasocket
- **Version**: 3.1.0
- **Build System**: Makefile
- **Build Status**: ✅ Built

## OpenHarmony Adaptation

### Conan Recipe

This package uses a Conan recipe (`conanfile.py`) for building and packaging on HarmonyOS.

- **Dependency**: lua/5.4.8 (from Conan artifact repository)
- **Compiler**: Obtained from Conan conf (clang)
- **Build target**: `make linux` (Makefile-based, no configure script)

### Key Adaptation Points

1. Uses clang compiler (from Conan conf) instead of default gcc
2. Lua include/library paths obtained from Conan dependency
3. Links against liblua.a, libm, libdl
4. test_package embeds Lua interpreter and loads modules via require()

### Usage

```lua
local socket = require("socket")
local client = socket.connect("example.com", 80)
```

## Dependencies

- **Required**: lua/5.4.8
