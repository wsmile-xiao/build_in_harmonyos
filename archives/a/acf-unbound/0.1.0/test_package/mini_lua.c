/* mini_lua.c — minimal Lua 5.4 runner for acf-unbound test harness.
 * Compiles against the conan lua/5.4.8 static lib; sets up arg global.
 * Usage: mini_lua <script.lua> [args...]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: mini_lua <script.lua> [args...]\n");
        return 2;
    }
    lua_State *L = luaL_newstate();
    if (!L) { fprintf(stderr, "cannot create lua state\n"); return 1; }
    luaL_openlibs(L);

    /* set arg global: arg[0]=script, arg[1..]=script args (like standard lua) */
    lua_newtable(L);
    for (int i = 1; i < argc; i++) {
        lua_pushstring(L, argv[i]);
        lua_rawseti(L, -2, i - 1);
    }
    lua_setglobal(L, "arg");

    int rc = luaL_loadfile(L, argv[1]);
    if (rc != LUA_OK) {
        fprintf(stderr, "SYNTAX/LOAD ERROR: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }
    rc = lua_pcall(L, 0, LUA_MULTRET, 0);
    if (rc != LUA_OK) {
        fprintf(stderr, "RUNTIME ERROR: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }
    lua_close(L);
    return 0;
}
