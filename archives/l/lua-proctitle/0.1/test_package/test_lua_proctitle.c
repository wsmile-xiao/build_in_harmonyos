#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>

#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>

#ifndef PROCTITLE_MODULE_DIR
#error "PROCTITLE_MODULE_DIR must be defined"
#endif

int main(void)
{
    const char *expected_name = "lua-proctitle";
    char cpath[1024];
    char process_name[16] = {0};
    lua_State *lua = luaL_newstate();

    if (lua == NULL) {
        fputs("failed to create Lua state\n", stderr);
        return 1;
    }
    luaL_openlibs(lua);
    snprintf(cpath, sizeof(cpath), "%s/?.so", PROCTITLE_MODULE_DIR);
    lua_getglobal(lua, "package");
    lua_pushstring(lua, cpath);
    lua_setfield(lua, -2, "cpath");
    lua_pop(lua, 1);

    if (luaL_dostring(lua,
            "local proctitle = assert(require('proctitle'))\n"
            "assert(type(proctitle) == 'function')\n"
            "proctitle('lua-proctitle')\n") != LUA_OK) {
        fprintf(stderr, "Lua test failed: %s\n", lua_tostring(lua, -1));
        lua_close(lua);
        return 1;
    }
    lua_close(lua);

    if (prctl(PR_GET_NAME, process_name, 0, 0, 0) != 0) {
        perror("prctl(PR_GET_NAME)");
        return 1;
    }
    if (strcmp(process_name, expected_name) != 0) {
        fprintf(stderr, "unexpected process name: %s\n", process_name);
        return 1;
    }
    puts("lua-proctitle consumer test passed");
    return 0;
}
