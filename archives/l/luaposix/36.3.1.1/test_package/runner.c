#include <stdio.h>

#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

int main(int argc, char **argv) {
    lua_State *state;

    if (argc != 2) {
        fprintf(stderr, "usage: %s test.lua\n", argv[0]);
        return 2;
    }
    state = luaL_newstate();
    if (state == NULL) {
        fputs("failed to create Lua state\n", stderr);
        return 2;
    }
    luaL_openlibs(state);
    if (luaL_dofile(state, argv[1]) != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(state, -1));
        lua_close(state);
        return 1;
    }
    lua_close(state);
    return 0;
}
