/* Minimal Lua interpreter for testing lua-sqlite module.
 * Compiled against the Conan lua/5.4.8 static library.
 * Usage: lua_test script.lua
 */
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include <stdio.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s script.lua\n", argv[0]);
        return 1;
    }
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "Failed to create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);
    if (luaL_dofile(L, argv[1]) != LUA_OK) {
        const char *err = lua_tostring(L, -1);
        if (err) fprintf(stderr, "%s\n", err);
        lua_close(L);
        return 1;
    }
    lua_close(L);
    return 0;
}
