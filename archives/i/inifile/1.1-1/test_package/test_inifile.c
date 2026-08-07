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
        "local inifile = require('inifile')\n"
        "local data, errors = inifile.parse('[section]\\nkey=value\\nflag=true\\n', 'memory')\n"
        "assert(not errors or #errors == 0)\n"
        "assert(data.section.key == 'value')\n"
        "assert(data.section.flag == true)\n"
        "assert(type(inifile.save('dummy', data, 'memory')) == 'string')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("inifile smoke ok");
    return 0;
}
