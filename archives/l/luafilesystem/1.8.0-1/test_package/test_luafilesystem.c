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

    const char *lua_cpath = getenv("LUA_CPATH");
    if (lua_cpath != NULL) {
        lua_getglobal(L, "package");
        lua_pushstring(L, lua_cpath);
        lua_setfield(L, -2, "cpath");
        lua_pop(L, 1);
    }

    const char *script =
        "local lfs = require('lfs')\n"
        "local cwd = lfs.currentdir()\n"
        "assert(type(cwd) == 'string' and #cwd > 0)\n"
        "local attr = lfs.attributes(cwd)\n"
        "assert(attr and attr.mode == 'directory')\n"
        "local count = 0\n"
        "for _ in lfs.dir('.') do count = count + 1 end\n"
        "assert(count > 0)\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "%s\n", message != NULL ? message : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("luafilesystem smoke ok");
    return 0;
}
