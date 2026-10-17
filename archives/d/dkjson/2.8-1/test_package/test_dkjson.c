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
        "local json = require('dkjson')\n"
        "assert(json.version == 'dkjson 2.8')\n"
        "local encoded = json.encode({hello = 'OHOS', n = 3, nested = {true, false}})\n"
        "assert(type(encoded) == 'string')\n"
        "local decoded, pos, err = json.decode(encoded, 1, nil)\n"
        "assert(err == nil, err)\n"
        "assert(decoded.hello == 'OHOS')\n"
        "assert(decoded.n == 3)\n"
        "assert(decoded.nested[1] == true and decoded.nested[2] == false)\n"
        "local pretty = json.encode({x = 1}, {indent = true})\n"
        "assert(pretty:match('\\n'))\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("dkjson smoke ok");
    return 0;
}

