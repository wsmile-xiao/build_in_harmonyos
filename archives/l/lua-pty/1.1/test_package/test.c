/*
 * test_package/test.c — L1 test for lua-pty
 *
 * Creates a Lua state, loads the pty.core module via dlopen, registers
 * it in package.preload, then calls require("pty.core") and tests
 * getenvs() to verify the module is functional.
 *
 * Usage: test_lua_pty <path-to-core.so>
 */
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "FAIL: Usage: %s <path-to-core.so>\n", argv[0]);
        return 1;
    }
    const char *so_path = argv[1];

    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "FAIL: Cannot create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    /* Load the module using dlopen */
    void *handle = dlopen(so_path, RTLD_NOW | RTLD_GLOBAL);
    if (!handle) {
        fprintf(stderr, "FAIL: Cannot load %s: %s\n", so_path, dlerror());
        lua_close(L);
        return 1;
    }

    /* Get the luaopen_pty_core function */
    typedef int (*luaopen_fn)(lua_State *L);
    luaopen_fn open_fn = (luaopen_fn)dlsym(handle, "luaopen_pty_core");
    if (!open_fn) {
        fprintf(stderr, "FAIL: Cannot find luaopen_pty_core: %s\n", dlerror());
        dlclose(handle);
        lua_close(L);
        return 1;
    }

    /* Register the module in package.preload so require() can find it */
    lua_getglobal(L, "package");
    lua_getfield(L, -1, "preload");
    lua_pushcfunction(L, (lua_CFunction)open_fn);
    lua_setfield(L, -2, "pty.core");
    lua_pop(L, 2);

    /* Test the module: require("pty.core") then call getenvs() */
    if (luaL_dostring(L,
        "local ok, pty = pcall(require, 'pty.core')\n"
        "if not ok then\n"
        "    print('FAIL: ' .. pty)\n"
        "    os.exit(1)\n"
        "end\n"
        "local envs = pty.getenvs()\n"
        "if type(envs) == 'table' then\n"
        "    print('PASS: pty.core loaded, getenvs returned table')\n"
        "    os.exit(0)\n"
        "else\n"
        "    print('FAIL: getenvs did not return table')\n"
        "    os.exit(1)\n"
        "end\n"
    ) != 0) {
        fprintf(stderr, "FAIL: Lua script error\n");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
