#include <dlfcn.h>
#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>
#include <stdio.h>
#include <string.h>

static int set_module_path(lua_State *state, const char *module)
{
    lua_getglobal(state, "package");
    if (!lua_istable(state, -1)) {
        fprintf(stderr, "Lua package table is unavailable\n");
        lua_pop(state, 1);
        return 0;
    }
    lua_pushstring(state, module);
    lua_setfield(state, -2, "cpath");
    lua_pop(state, 1);
    return 1;
}

static int run_script(lua_State *state, const char *script)
{
    if (luaL_loadfile(state, script) != 0) {
        fprintf(stderr, "loadfile(%s) failed: %s\n", script,
                lua_tostring(state, -1));
        return 0;
    }
    if (lua_pcall(state, 0, 0, 0) != 0) {
        fprintf(stderr, "script %s failed: %s\n", script,
                lua_tostring(state, -1));
        return 0;
    }
    return 1;
}

static int run_upstream(const char *executable, const char *runner,
                        const char *module, const char *source)
{
    void *handle = dlopen(module, RTLD_NOW | RTLD_GLOBAL);
    lua_State *state;

    if (handle == NULL) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", module, dlerror());
        return 0;
    }
    if (dlsym(handle, "luaopen_mpack") == NULL) {
        fprintf(stderr, "dlsym(luaopen_mpack) failed: %s\n", dlerror());
        dlclose(handle);
        return 0;
    }

    state = luaL_newstate();
    if (state == NULL) {
        fprintf(stderr, "luaL_newstate failed\n");
        dlclose(handle);
        return 0;
    }
    luaL_openlibs(state);
    if (!set_module_path(state, module)) {
        lua_close(state);
        dlclose(handle);
        return 0;
    }

    lua_pushstring(state, executable);
    lua_setglobal(state, "LMPACK_RUNNER_EXECUTABLE");
    lua_pushstring(state, module);
    lua_setglobal(state, "LMPACK_MODULE");
    lua_pushstring(state, source);
    lua_setglobal(state, "LMPACK_UPSTREAM_SOURCE");

    if (!run_script(state, runner)) {
        lua_close(state);
        dlclose(handle);
        return 0;
    }
    lua_close(state);
    dlclose(handle);
    return 1;
}

int main(int argc, char **argv)
{
    if (argc == 4 && strcmp(argv[1], "--upstream-child") == 0) {
        lua_State *state = luaL_newstate();
        int result;
        if (state == NULL) {
            fprintf(stderr, "luaL_newstate failed\n");
            return 1;
        }
        luaL_openlibs(state);
        if (!set_module_path(state, argv[2])) {
            lua_close(state);
            return 1;
        }
        result = run_script(state, argv[3]);
        lua_close(state);
        return result ? 0 : 1;
    }

    if (argc != 4) {
        fprintf(stderr,
                "usage: %s <runner.lua> <mpack.so> <upstream-test.lua>\n",
                argv[0]);
        return 2;
    }
    return run_upstream(argv[0], argv[1], argv[2], argv[3]) ? 0 : 1;
}
