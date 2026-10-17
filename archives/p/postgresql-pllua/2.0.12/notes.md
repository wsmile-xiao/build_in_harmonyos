# notes for REL_2_0_12

## Build System
PGXS (PostgreSQL Extension Makefile). Uses `pg_config --pgxs` to locate
the PGXS makefile and `include $(PGXS)`.

## Dependencies
- PostgreSQL 18.3: vendored from source (same pattern as postgresql-topn/2.7.0).
  Full server build provides pg_config + PGXS + server headers + postgres/initdb/pg_ctl.
  HarmonyOS adaptation patch applied (SysV shm skip, hmdfs perm relax, Unix socket disable).
- Lua 5.4.8: vendored from source (static library + interpreter/compiler).
  Built with `make generic CC=clang MYCFLAGS="-O3 -fPIC -DLUA_USE_POSIX -DLUA_USE_DLOPEN"`.
  Provides liblua.a, lua, luac, and headers (lua.h, lualib.h, lauxlib.h, luaconf.h).

## Build
pllua Makefile variables set:
- LUA_INCDIR = vendored Lua include dir
- LUALIB = "-L<vendored Lua lib> -llua -ldl -lm"
- LUA = vendored lua binary (for build-time codegen: functable.lua, errcodes.lua)
- LUAC = vendored luac binary (for compiling compat.lua to .luac)
- PG_CONFIG = bootstrapped pg_config
- PGXS = bootstrapped pgxs.mk

PG_LDFLAGS = "-Wl,--unresolved-symbols=ignore-all -Wl,--allow-shlib-undefined"
(PG server symbols are undefined until the postgres process loads the extension
at CREATE EXTENSION time.)

## Artifacts
- pllua.so (shared library, linked into PostgreSQL at CREATE EXTENSION time)
- pllua.control, plluau.control (extension control files)
- pllua--2.0.sql, plluau--2.0.sql, pllua--1.0--2.0.sql, plluau--1.0--2.0.sql (SQL scripts)

## Lua Version Compatibility
pllua supports Lua 5.1/LuaJIT, 5.3, 5.4 (but NOT 5.4.5 due to API break).
Lua 5.4.8 (release num 50408 != 50405) is compatible.

## HarmonyOS Adaptation
No pllua-specific patches needed. The PostgreSQL harmony patch handles all
platform issues (SysV shm, hmdfs permissions, Unix sockets, DSM mmap, getpwuid).
Lua builds cleanly with standard POSIX flags.

## 结束
Build completed successfully. pllua.so built and verified.
