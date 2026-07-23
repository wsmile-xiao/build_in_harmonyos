#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>

#include <stdio.h>

int main(void) {
    lua_State *state = luaL_newstate();
    if (state == NULL) {
        fprintf(stderr, "luaL_newstate failed\n");
        return 1;
    }

    luaL_openlibs(state);
    if (luaL_dostring(state, "return 6 * 7") != LUA_OK) {
        fprintf(stderr, "luaL_dostring failed: %s\n", lua_tostring(state, -1));
        lua_close(state);
        return 2;
    }

    if (!lua_isinteger(state, -1) || lua_tointeger(state, -1) != 42) {
        fprintf(stderr, "Lua returned an unexpected result\n");
        lua_close(state);
        return 3;
    }

    lua_close(state);
    return 0;
}
