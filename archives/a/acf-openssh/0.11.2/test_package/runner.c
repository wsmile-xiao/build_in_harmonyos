/* Minimal Lua 5.4 runner used only by the Conan consumer test. */
#include <stdio.h>
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

static void set_args(lua_State *state, int argc, char **argv) {
    lua_newtable(state);
    lua_pushinteger(state, argc - 2);
    lua_setfield(state, -2, "n");
    for (int index = 1; index < argc; ++index) {
        lua_pushstring(state, argv[index]);
        lua_rawseti(state, -2, index - 1);
    }
    lua_setglobal(state, "arg");
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s script.lua [args...]\n", argv[0]);
        return 2;
    }

    lua_State *state = luaL_newstate();
    if (!state) {
        fputs("cannot create Lua state\n", stderr);
        return 1;
    }
    luaL_openlibs(state);
    set_args(state, argc, argv);

    if (luaL_loadfile(state, argv[1]) != LUA_OK ||
        lua_pcall(state, 0, LUA_MULTRET, 0) != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(state, -1));
        lua_close(state);
        return 1;
    }
    lua_close(state);
    return 0;
}
