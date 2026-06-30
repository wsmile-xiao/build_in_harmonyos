# lua-pc

Lua is a powerful, efficient, lightweight, embeddable scripting language. It supports procedural programming, object-oriented programming, functional programming, data-driven programming, and data description.

## Description

Lua combines simple procedural syntax with powerful data description constructs based on associative arrays and extensible semantics. Lua is dynamically typed, runs by interpreting bytecode with a register-based virtual machine, and has automatic memory management with incremental garbage collection, making it ideal for configuration, scripting, and rapid prototyping.

This is the PC version compiled for OpenHarmony/HarmonyOS.

## Version

- 5.4.7 (current)

## Dependencies

None - Lua is self-contained and does not require external libraries beyond the standard C library and math library.

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-pc 5.4.7
```

## Verification

```bash
lua -v
# Expected output: Lua 5.4.7  Copyright (C) 1994-2024 Lua.org, PUC-Rio
```

## Components

- **lua**: Lua interpreter
- **luac**: Lua compiler
- **liblua.a**: Static library for embedding

## Build Notes

- Built with clang on OpenHarmony
- Modified Makefile to use `cp -p` instead of `install -p` (OpenHarmony lacks GNU install command)
- Uses `linux` platform target with custom compiler flags

## License

MIT License

## Homepage

https://www.lua.org/