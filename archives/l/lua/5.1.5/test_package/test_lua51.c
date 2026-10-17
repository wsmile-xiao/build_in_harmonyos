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

    if (luaL_loadstring(
            state,
            "local name = assert(os.tmpname()); "
            "local file = assert(io.open(name, 'w')); "
            "assert(file:write('openharmony')); "
            "assert(file:close()); "
            "assert(os.remove(name)); "
            "return type(name)") != 0 ||
        lua_pcall(state, 0, 1, 0) != 0) {
        fprintf(stderr, "TMPDIR-aware os.tmpname test failed: %s\n",
                lua_tostring(state, -1));
        lua_close(state);
        return 7;
    }

    if (!lua_isstring(state, -1) ||
        strcmp(lua_tostring(state, -1), "string") != 0) {
        fprintf(stderr, "os.tmpname returned an unexpected value\n");
        lua_close(state);
        return 8;
    }
    lua_pop(state, 1);

    if (luaL_loadstring(
            state,
            "local file = assert(io.tmpfile()); "
            "assert(file:write('openharmony')); "
            "assert(file:seek('set', 0)); "
            "local value = assert(file:read('*a')); "
            "assert(file:close()); "
            "return value") != 0 ||
        lua_pcall(state, 0, 1, 0) != 0) {
        fprintf(stderr, "TMPDIR-aware io.tmpfile test failed: %s\n",
                lua_tostring(state, -1));
        lua_close(state);
        return 9;
    }

    if (!lua_isstring(state, -1) ||
        strcmp(lua_tostring(state, -1), "openharmony") != 0) {
        fprintf(stderr, "io.tmpfile returned unexpected data\n");
        lua_close(state);
        return 10;
    }
    lua_pop(state, 1);

    lua_close(state);
    return 0;
}
