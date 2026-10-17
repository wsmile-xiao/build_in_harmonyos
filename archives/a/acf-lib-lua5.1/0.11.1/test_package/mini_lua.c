#include <stdio.h>

#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

static void set_args(lua_State *state, int argc, char **argv) {
    int index;
    lua_newtable(state);
    lua_pushinteger(state, argc - 2);
    lua_setfield(state, -2, "n");
    for (index = 1; index < argc; ++index) {
        lua_pushstring(state, argv[index]);
        lua_rawseti(state, -2, index - 1);
    }
    lua_setglobal(state, "arg");
}

int main(int argc, char **argv) {
    const char *message;
    lua_State *state;
    int status;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <script.lua> [args...]\n", argv[0]);
        return 2;
    }

    state = luaL_newstate();
    if (state == NULL) {
        fprintf(stderr, "cannot create Lua state\n");
        return 3;
    }
    luaL_openlibs(state);
    set_args(state, argc, argv);

    status = luaL_loadfile(state, argv[1]);
    if (status == 0) {
        status = lua_pcall(state, 0, LUA_MULTRET, 0);
    }
    if (status != 0) {
        message = lua_tostring(state, -1);
        fprintf(stderr, "%s\n", message != NULL ? message : "unknown Lua error");
        lua_close(state);
        return 1;
    }

    lua_close(state);
    return 0;
}
