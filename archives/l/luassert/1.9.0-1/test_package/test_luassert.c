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
        "local luaassert = require('luassert')\n"
        "luaassert.are.equal(1, 1)\n"
        "luaassert.is.True(true)\n"
        "luaassert.has.errors(function() error('expected') end)\n"
        "local spy = require('luassert.spy')\n"
        "local s = spy.new(function(value) return value end)\n"
        "luaassert.are.equal('ok', s('ok'))\n"
        "luaassert.spy(s).was.called(1)\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("luassert smoke ok");
    return 0;
}

