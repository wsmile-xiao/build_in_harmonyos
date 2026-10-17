# acf-lib-lua5.5

Lua 5.5 modules from the Alpine Configuration Framework standard library.

The package installs the eight upstream modules below
`share/lua/5.5/acf/`, preserves the upstream top-level compatibility module
names below `share/lua/5.5/`, and exports the search path through `LUA_PATH`.

The modules `acf.format`, `acf.html`, and `acf.validator` use only Lua's
standard library. Other modules expose optional system-facing features that
require POSIX, subprocess, or database-driver modules at runtime.
