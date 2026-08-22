/*
 * Test program for lua-toml 1.0 — uses the Lua C API to load
 * toml.lua and verify parse/encode functionality.
 *
 * toml.lua is copied to the build directory by the test_package
 * conanfile.py generate() step, so package.path = "./?.lua;" finds it.
 */
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
#include <stdio.h>

int main(void)
{
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "Failed to create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    /* Set package.path so require('toml') finds ./toml.lua */
    lua_getglobal(L, "package");
    lua_pushstring(L, "./?.lua;");
    lua_setfield(L, -2, "path");
    lua_pop(L, 1);

    /*
     * Test 1: Parse a TOML string and check the result.
     * Test 2: Encode a Lua table and check the output contains the key.
     */
    const char *test_code =
        "local toml = require('toml')\n"
        "local data = toml.parse('key = \"value\"')\n"
        "assert(data.key == 'value', 'Parse test failed: expected value, got ' .. tostring(data.key))\n"
        "local encoded = toml.encode({key = 'value'})\n"
        "assert(string.find(encoded, 'key'), 'Encode test failed: key not found in output')\n"
        "print('All lua-toml tests passed')\n";

    if (luaL_dostring(L, test_code) != LUA_OK) {
        fprintf(stderr, "Test failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
