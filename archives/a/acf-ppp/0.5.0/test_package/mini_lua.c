/* Minimal Lua 5.4 script runner for the acf-ppp test harness. */
#include <stdio.h>
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

static void set_args(lua_State *state, int argc, char **argv) {
    lua_newtable(state);
    for (int index = 1; index < argc; ++index) {
        lua_pushstring(state, argv[index]);
        lua_rawseti(state, -2, index - 1);
    }
    lua_setglobal(state, "arg");
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: lua-runner script.lua [args...]\n");
        return 2;
    }

    lua_State *state = luaL_newstate();
    if (!state) {
        fprintf(stderr, "cannot create Lua state\n");
        return 1;
    }
    luaL_openlibs(state);
    set_args(state, argc, argv);

    int result = luaL_loadfile(state, argv[1]);
    if (result == LUA_OK) {
        result = lua_pcall(state, 0, LUA_MULTRET, 0);
    }
    if (result != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(state, -1));
        lua_close(state);
        return 1;
    }

    lua_close(state);
    return 0;
}
