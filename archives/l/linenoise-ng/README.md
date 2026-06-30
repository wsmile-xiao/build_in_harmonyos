# Linenoise-NG

A small, portable GNU readline replacement for Linux, Windows and MacOS which is capable of handling UTF-8 characters. Uses C++ internally but provides a pure C interface compatible with the original linenoise API.

## Origin

Based on the work by Salvatore Sanfilippo (antirez/linenoise) and 10gen Inc. (ArangoDB). BSD licensed.

## Features

- Single-line and multi-line editing mode with usual key bindings
- History handling
- Completion
- BSD license source code
- Only uses a subset of VT100 escapes (ANSI.SYS compatible)
- UTF8 aware
- Support for Linux, MacOS and Windows

## Build

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j1
make install
```

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1 | built | 2026-06-25 |
