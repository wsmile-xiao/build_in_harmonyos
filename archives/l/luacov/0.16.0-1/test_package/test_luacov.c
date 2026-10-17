#include <stdio.h>
#include <stdlib.h>

#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (L == NULL) {
        fputs("failed to create Lua state\n", stderr);
        return 1;
    }
    luaL_openlibs(L);

    const char *lua_path = getenv("LUA_PATH");
    if (lua_path != NULL) {
        lua_getglobal(L, "package");
        lua_pushstring(L, lua_path);
        lua_setfield(L, -2, "path");
        lua_pop(L, 1);
    }

    const char *script =
        "local luacov = require('luacov')\n"
        "local runner = require('luacov.runner')\n"
        "assert(type(luacov) == 'table')\n"
        "assert(type(runner) == 'table')\n"
        "assert(runner.version == '0.16.0')\n"
        "assert(type(require('luacov.stats')) == 'table')\n"
        "assert(type(require('datafile')) == 'table')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "%s\n", message != NULL ? message : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("luacov smoke ok");
    return 0;
}
