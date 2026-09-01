/*
 * test_package for luajit-openresty — verifies library linking,
 * LuaJIT JIT engine, and FFI (unique to LuaJIT vs standard Lua).
 */
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "FAIL: luaL_newstate returned NULL\n");
        return 1;
    }
    luaL_openlibs(L);

    /* 1. Basic Lua execution */
    if (luaL_dostring(L, "print('[test] basic Lua OK')") != LUA_OK) {
        fprintf(stderr, "FAIL: basic Lua: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* 2. Verify this is LuaJIT (not standard Lua) via jit.version */
    if (luaL_dostring(L,
        "if not jit then error('jit table missing — not LuaJIT') end\n"
        "print('[test] jit.version = ' .. jit.version)\n"
    ) != LUA_OK) {
        fprintf(stderr, "FAIL: jit check: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* 3. Verify FFI works (LuaJIT-specific) */
    if (luaL_dostring(L,
        "local ffi = require('ffi')\n"
        "ffi.cdef('int printf(const char *fmt, ...);')\n"
        "ffi.C.printf('[test] FFI printf: OK\\n')\n"
    ) != LUA_OK) {
        fprintf(stderr, "FAIL: FFI test: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    printf("[test] ALL CHECKS PASSED\n");
    return 0;
}
