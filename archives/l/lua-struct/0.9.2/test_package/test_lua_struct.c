#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (L == NULL) {
        fputs("failed to create Lua state\n", stderr);
        return 1;
    }
    luaL_openlibs(L);

    /* Set package.path from LUA_PATH env so require("struct") works */
    const char *lua_path = getenv("LUA_PATH");
    if (lua_path != NULL) {
        lua_getglobal(L, "package");
        lua_pushstring(L, lua_path);
        lua_setfield(L, -2, "path");
        lua_pop(L, 1);
    }

    const char *script =
        "local struct = require('struct')\n"
        /* Test pack/unpack round-trip for various types */
        "local packed = struct.pack('<IhB', 123456789, -3200, 255)\n"
        "local I, h, B = struct.unpack('<IhB', packed)\n"
        "assert(I == 123456789, 'I mismatch: ' .. tostring(I))\n"
        "assert(h == -3200, 'h mismatch: ' .. tostring(h))\n"
        "assert(B == 255, 'B mismatch: ' .. tostring(B))\n"
        /* Test string pack/unpack */
        "local s = 'hello'\n"
        "local sp = struct.pack('<s', s)\n"
        "local us = struct.unpack('<s', sp)\n"
        "assert(us == s, 'string mismatch: ' .. tostring(us))\n"
        /* Test big-endian */
        "local be = struct.pack('>I', 42)\n"
        "local bev = struct.unpack('>I', be)\n"
        "assert(bev == 42, 'big-endian mismatch: ' .. tostring(bev))\n"
        /* Test float/double */
        "local f = 3.14\n"
        "local fp = struct.pack('<f', f)\n"
        "local fv = struct.unpack('<f', fp)\n"
        "assert(math.abs(fv - f) < 0.01, 'float mismatch')\n"
        /* Test long (use value within double precision, < 2^53) */
        "local L = 1234567890123\n"
        "local Lp = struct.pack('<L', L)\n"
        "local Lv = struct.unpack('<L', Lp)\n"
        "assert(Lv == L, 'long mismatch: ' .. tostring(Lv))\n"
        "print('lua-struct smoke ok')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "%s\n", message != NULL ? message : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
