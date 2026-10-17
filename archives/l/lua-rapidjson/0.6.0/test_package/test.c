#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
#include <stdio.h>

#ifndef RAPIDJSON_LIB_DIR
#error "RAPIDJSON_LIB_DIR must be defined"
#endif

int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "FAIL: cannot create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    /* Set package.cpath to find rapidjson.so */
    lua_getglobal(L, "package");
    lua_getfield(L, -1, "cpath");
    const char *cpath = lua_tostring(L, -1);
    lua_pushfstring(L, "%s/?.so;%s", RAPIDJSON_LIB_DIR, cpath);
    lua_setfield(L, -3, "cpath");
    lua_pop(L, 2);

    /* Test 1: Load rapidjson module */
    if (luaL_dostring(L, "return require('rapidjson')") != 0) {
        fprintf(stderr, "FAIL: require('rapidjson'): %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* Test 2: Decode JSON object */
    if (luaL_dostring(L,
        "local rj = require('rapidjson')\n"
        "local d = rj.decode('{\"key\":\"value\",\"num\":42}')\n"
        "assert(d.key == 'value', 'decode key mismatch')\n"
        "assert(d.num == 42, 'decode num mismatch')\n"
        "return true") != 0) {
        fprintf(stderr, "FAIL: decode test: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* Test 3: Encode JSON and round-trip */
    if (luaL_dostring(L,
        "local rj = require('rapidjson')\n"
        "local s = rj.encode({key='value', num=42})\n"
        "assert(type(s) == 'string', 'encode result not string')\n"
        "local d = rj.decode(s)\n"
        "assert(d.key == 'value', 'round-trip key mismatch')\n"
        "assert(d.num == 42, 'round-trip num mismatch')\n"
        "return true") != 0) {
        fprintf(stderr, "FAIL: encode test: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* Test 4: Decode array */
    if (luaL_dostring(L,
        "local rj = require('rapidjson')\n"
        "local d = rj.decode('[1, 2, 3, \"four\", true]')\n"
        "assert(d[1] == 1, 'array[1] mismatch')\n"
        "assert(d[2] == 2, 'array[2] mismatch')\n"
        "assert(d[3] == 3, 'array[3] mismatch')\n"
        "assert(d[4] == 'four', 'array[4] mismatch')\n"
        "assert(d[5] == true, 'array[5] mismatch')\n"
        "return true") != 0) {
        fprintf(stderr, "FAIL: array decode test: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* Test 5: Null handling */
    if (luaL_dostring(L,
        "local rj = require('rapidjson')\n"
        "local d = rj.decode('{\"x\":null}')\n"
        "assert(d.x == rj.null, 'null mismatch')\n"
        "return true") != 0) {
        fprintf(stderr, "FAIL: null test: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    printf("PASS: All rapidjson tests passed\n");
    lua_close(L);
    return 0;
}
