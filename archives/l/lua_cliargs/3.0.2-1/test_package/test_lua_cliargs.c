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
        "local cli = require('cliargs.core')()\n"
        "cli:argument('ARG', 'argument description')\n"
        "local result = cli:parse({'value'})\n"
        "assert(result.ARG == 'value')\n"
        "local public_cli = require('cliargs')\n"
        "assert(public_cli.VERSION == '3.0.2')\n"
        "local f = assert(io.open('cliargs-smoke.ini', 'w'))\n"
        "f:write('[cli]\\nmode=fast\\n')\n"
        "f:close()\n"
        "local loader = require('cliargs.config_loader')\n"
        "local config = assert(loader.from_ini('cliargs-smoke.ini'))\n"
        "assert(config.mode == 'fast')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("lua_cliargs smoke ok");
    return 0;
}
