#include <dlfcn.h>
#include <lauxlib.h>
#include <lualib.h>
#include <stdio.h>

typedef int (*luaopen_fn)(lua_State *state);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <luv.so>\n", argv[0]);
        return 1;
    }

    lua_State *state = luaL_newstate();
    if (!state) {
        fputs("failed to create Lua state\n", stderr);
        return 1;
    }
    luaL_openlibs(state);

    void *module = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    if (!module) {
        fprintf(stderr, "failed to load luv module: %s\n", dlerror());
        lua_close(state);
        return 1;
    }

    luaopen_fn open_luv = (luaopen_fn)dlsym(module, "luaopen_luv");
    if (!open_luv) {
        fprintf(stderr, "luaopen_luv is missing: %s\n", dlerror());
        lua_close(state);
        dlclose(module);
        return 1;
    }

    lua_pushcfunction(state, (lua_CFunction)open_luv);
    lua_setglobal(state, "open_luv");
    const char *script =
        "local uv = open_luv()\n"
        "assert(type(uv.version_string) == 'function')\n"
        "assert(type(uv.version_string()) == 'string')\n"
        "local timer, fired = uv.new_timer(), false\n"
        "timer:start(1, 0, function() fired = true; timer:close() end)\n"
        "uv.run()\n"
        "assert(fired)\n";
    if (luaL_dostring(state, script) != LUA_OK) {
        const char *error_message = lua_tostring(state, -1);
        fprintf(stderr, "Lua test failed: %s\n", error_message ? error_message : "unknown Lua error");
        lua_close(state);
        dlclose(module);
        return 1;
    }

    puts("lua-luv consumer test passed");
    /* Lua finalizers can still reference functions implemented by luv.so. */
    lua_close(state);
    dlclose(module);
    return 0;
}
