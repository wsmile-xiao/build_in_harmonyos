# kakoune

Kakoune is a modal text editor inspired by Vim. It focuses on interaction as a text editing language, providing more expressive and concise editing commands.

## Key Features
- Modal editing with Vim-like paradigm
- Selection-first approach (select then act)
- Multiple selections support
- Powerful scripting language
- Lightweight and fast

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 2025.06.03 | built | 2026-05-27 |

## Build System
- Custom POSIX Makefile (not autotools/cmake)
- Compile: `make PREFIX=$DEFAULT_PREFIX CXX=clang++`
- Install: `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX gzip_man=no`

## Known Issues on HarmonyOS
- HMDFS does not support `ln -sf` (use `rm -f && ln -s`)
- C++2b mode requires explicit `#include <cstdio>` for `rename()`
- Test suite requires terminal environment (headless incomplete)