#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    lua_State *state = luaL_newstate();
    if (state == NULL) {
        fprintf(stderr, "luaL_newstate failed\n");
        return 1;
    }

    luaL_openlibs(state);
    if (luaL_loadstring(state, "return math.sqrt(1764)") != 0 ||
        lua_pcall(state, 0, 1, 0) != 0) {
        fprintf(stderr, "Lua math library failed: %s\n", lua_tostring(state, -1));
        lua_close(state);
        return 2;
    }

    if (!lua_isnumber(state, -1) || (int)lua_tonumber(state, -1) != 42) {
        fprintf(stderr, "Lua math library returned an unexpected result\n");
        lua_close(state);
        return 3;
    }
    lua_pop(state, 1);

    lua_getglobal(state, "_VERSION");
    const char *version = lua_tostring(state, -1);
    if (version == NULL || strcmp(version, "Lua 5.1") != 0) {
        fprintf(stderr, "unexpected Lua version: %s\n", version ? version : "(nil)");
        lua_close(state);
        return 4;
    }
    lua_pop(state, 1);

    lua_getglobal(state, "package");
    if (!lua_istable(state, -1)) {
        fprintf(stderr, "package table is not available\n");
        lua_close(state);
        return 5;
    }
    lua_pop(state, 1);

    lua_getglobal(state, "require");
    if (!lua_isfunction(state, -1)) {
        fprintf(stderr, "require function is not available\n");
        lua_close(state);
        return 6;
    }
    lua_pop(state, 1);

    lua_close(state);
    return 0;
}
