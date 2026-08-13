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
        const char *message = lua_tostring(state, -1);
        fprintf(stderr, "luaL_dostring failed: %s\n",
                message != NULL ? message : "(unknown error)");
        lua_close(state);
        return 2;
    }

    // Lua 5.2 无 lua_isinteger（5.3+ 才引入），用 lua_type + lua_tonumber
    // 做版本兼容检查：结果必须是 number 且数值为 42。
    if (lua_type(state, -1) != LUA_TNUMBER || lua_tonumber(state, -1) != 42.0) {
        fprintf(stderr, "Lua returned an unexpected result\n");
        lua_close(state);
        return 3;
    }

    lua_close(state);
    return 0;
}
