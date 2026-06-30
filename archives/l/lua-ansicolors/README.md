# lua-ansicolors

ANSI terminal color manipulation library for Lua.

## Description

lua-ansicolors is a simple Lua function for printing to the console in color. It provides an easy-to-use interface for ANSI escape codes.

## Features

- Simple color printing for terminal output
- Support for foreground colors (black, red, green, yellow, blue, magenta, cyan, white)
- Support for background colors
- Support for text attributes (bright, dim, underline, blink, reverse, hidden)

## Usage

```lua
local colors = require 'ansicolors'
print(colors('%{red}hello'))
print(colors('%{redbg}hello%{reset}'))
print(colors('%{bright red underlined}hello'))
```

## Dependencies

- Lua >= 5.1

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.0.2 | published | 2026-06-17 |

## License

MIT License