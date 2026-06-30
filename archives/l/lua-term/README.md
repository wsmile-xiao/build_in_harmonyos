# lua-term

Terminal operations for Lua.

## Description

lua-term is a Lua module for manipulating a terminal. It provides:
- Terminal colors (foreground and background)
- Cursor movement and positioning
- Screen clearing operations
- TTY detection

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.7 | built | 2026-06-09 | Lua 5.4 支持，HMDFS 兼容补丁 |

## Installation

Precompiled package available at:
```
archives/l/lua-term/0.7/packaging/lua-term-0.7-ohos-aarch64.tar.gz
```

Install using cmd-pkgs script:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-term 0.7
```

After installation, set Lua environment variables:
```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;/storage/Users/currentUser/usr/local/share/lua/5.4/?/init.lua;;"
export LUA_CPATH="/storage/Users/currentUser/usr/local/lib/lua/5.4/?.so;;"
```

## Dependencies

- Lua 5.4.7

## Usage Example

```lua
local term = require 'term'
local colors = term.colors

print(term.isatty(io.stdout))  -- true if stdout is a TTY

print(colors.red 'hello')
print(colors.red .. 'hello' .. colors.reset)

term.clear()    -- clear screen
term.cursor.jump(1, 1)  -- move cursor to (1, 1)
```

## Known Issues

1. HMDFS file system doesn't support symbolic links (ln -s), patched with cp
2. Lua search path defaults to /usr/local, requires environment variable adjustment

## Build System

- Type: makefile
- Compiler: clang
- Patches: 1 (0001-Makefile.patch)

## References

- Source: https://github.com/hoelzro/lua-term
- License: MIT (COPYING file)