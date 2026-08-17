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
    const char *lua_cpath = getenv("LUA_CPATH");
    if (lua_cpath != NULL) {
        lua_getglobal(L, "package");
        lua_pushstring(L, lua_cpath);
        lua_setfield(L, -2, "cpath");
        lua_pop(L, 1);
    }

    const char *script =
        "local term = require('term')\n"
        "assert(type(term.isatty(io.stdout)) == 'boolean')\n"
        "assert(type(term.colors) == 'table')\n"
        "assert(type(term.cursor) == 'table')\n"
        "assert(type(term.clear) == 'function')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        const char *error = lua_tostring(L, -1);
        fprintf(stderr, "%s\n", error != NULL ? error : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("lua-term smoke ok");
    return 0;
}
