/*
 * test_subprocess.c — L1 test for lua-subprocess
 *
 * Embeds Lua, loads the subprocess module, spawns 'echo hello',
 * reads stdout, and verifies the output contains 'hello'.
 */

#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "Failed to create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    /* Lua script: require subprocess, popen echo with PIPE, verify output */
    const char *script =
        "local sp = require('subprocess')\n"
        "local p = sp.popen {'echo', 'hello_from_subprocess', stdout = sp.PIPE}\n"
        "local out = p.stdout:read('*a')\n"
        "p:wait()\n"
        "if string.find(out, 'hello_from_subprocess') then\n"
        "    print('TEST PASSED: subprocess module works')\n"
        "else\n"
        "    print('TEST FAILED: unexpected output: ' .. out)\n"
        "    os.exit(1)\n"
        "end\n";

    int result = luaL_dostring(L, script);
    if (result != LUA_OK) {
        fprintf(stderr, "Lua error: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
