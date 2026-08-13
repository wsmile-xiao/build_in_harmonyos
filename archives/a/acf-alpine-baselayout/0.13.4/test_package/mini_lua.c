/* mini_lua.c — minimal Lua 5.4 script runner for the acf-alpine-baselayout
 * test harness. Links against the conan lua/5.4.8 static library. Runs a Lua
 * chunk from a file argument (or -e). Sets the `arg` global like the official
 * interpreter: arg[0]=script, arg[1..n]=script args. Not shipped with the
 * package — test-only driver. */
#include <stdio.h>
#include <string.h>
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

static int script_argc;
static char **script_argv;

static void set_args(lua_State *L) {
    int n = script_argc;
    lua_newtable(L);
    lua_pushinteger(L, n);
    lua_setfield(L, -2, "n");
    for (int i = 0; i <= n; i++) {
        lua_pushstring(L, script_argv[i]);
        lua_rawseti(L, -2, i);
    }
    lua_setglobal(L, "arg");
}

int main(int argc, char **argv) {
    lua_State *L = luaL_newstate();
    if (!L) { fprintf(stderr, "cannot create lua state\n"); return 1; }
    luaL_openlibs(L);

    int i = 1;
    if (argc > 1 && strcmp(argv[1], "-e") == 0 && argc > 2) {
        script_argc = argc - 3;
        script_argv = argv + 2;
        set_args(L);
        if (luaL_dostring(L, argv[2]) != LUA_OK) {
            fprintf(stderr, "%s\n", lua_tostring(L, -1));
            return 1;
        }
        lua_close(L);
        return 0;
    }
    if (argc > 1) {
        script_argc = argc - 2;
        script_argv = argv + 1;
        set_args(L);
        if (luaL_loadfile(L, argv[1]) != LUA_OK ||
            lua_pcall(L, 0, LUA_MULTRET, 0) != LUA_OK) {
            fprintf(stderr, "%s\n", lua_tostring(L, -1));
            return 1;
        }
    } else {
        script_argc = 0;
        script_argv = argv;
        set_args(L);
        if (luaL_loadfile(L, NULL) != LUA_OK ||
            lua_pcall(L, 0, LUA_MULTRET, 0) != LUA_OK) {
            fprintf(stderr, "%s\n", lua_tostring(L, -1));
            return 1;
        }
    }
    lua_close(L);
    return 0;
}
