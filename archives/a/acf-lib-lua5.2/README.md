# acf-lib-lua5.2

Lua 5.2 modules from the Alpine Configuration Framework standard library.

The package installs the eight upstream modules below
`share/lua/5.2/acf/`, preserves the upstream top-level compatibility module
names below `share/lua/5.2/`, and exports the search path through `LUA_PATH`.

The modules `acf.format`, `acf.html`, and `acf.validator` use only Lua's
standard library. Other modules expose optional system-facing features that
require POSIX, subprocess, or database-driver modules at runtime.

## OHOS adaptation

- Pure-Lua data package: no compilation. `package()` copies the eight `.lua`
  modules into `share/lua/5.2/acf` and duplicates the top-level compatibility
  names, then `package_info()` exports `LUA_PATH` via buildenv/runenv.
- Lua 5.2 keeps generic-for loop variables mutable, so the 
  `0001-lua55-mutable-loop-values.patch` that the Lua 5.5 port needs is **not**
  required here.

## Dependencies

- `lua/5.2.4` (runtime interpreter/library for consumers)

## References

- Upstream: https://gitlab.alpinelinux.org/acf/acf-lib
