#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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
        "local colors = require('ansicolors')\n"
        "local c27 = string.char(27)\n"
        "assert(colors('foo') == c27 .. '[0mfoo' .. c27 .. '[0m')\n"
        "assert(colors('%{red}foo') == c27 .. '[0m' .. c27 .. '[31mfoo' .. c27 .. '[0m')\n"
        "assert(colors.noReset('foo') == 'foo')\n"
        "assert(colors.noReset('%{red}foo') == c27 .. '[31mfoo')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "%s\n", message != NULL ? message : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("lua-ansicolors smoke ok");
    return 0;
}
