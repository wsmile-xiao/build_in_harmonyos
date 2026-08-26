# lua-struct

Implementation of binary packing/unpacking in pure Lua.

- **Homepage**: https://github.com/iryont/lua-struct
- **License**: MIT/X11
- **Build system**: Pure Lua (no compilation)

## Available versions

| Version | Status |
|---------|--------|
| 0.9.2 | pending OHOS validation |

## Description

lua-struct provides Lua functions for packing and unpacking binary data,
similar to PHP's `pack()` and `unpack()` functions. It supports:

- Signed/unsigned bytes, shorts, ints, longs (b/B/h/H/i/I/l/L)
- Floats and doubles (f/d)
- Zero-terminated strings (s)
- Fixed-length strings (cn)
- Little/big endian byte order (< and >)

## Dependencies

- Lua 5.4 (runtime only, for test_package)
