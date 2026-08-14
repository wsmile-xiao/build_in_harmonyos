#include <stdio.h>
#include <stdlib.h>
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (L == NULL) {
        fprintf(stderr, "ERROR: Failed to create Lua state\n");
        return 1;
    }

    luaL_openlibs(L);

    /* Run a simple Lua expression and check the result */
    const char *script = "return 1 + 2";
    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "ERROR: Lua execution failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_Integer result = lua_tointeger(L, -1);
    if (result != 3) {
        fprintf(stderr, "ERROR: Expected 3, got %lld\n", (long long)result);
        lua_close(L);
        return 1;
    }

    printf("lua-pc 5.4.7 test: OK (1+2=%lld)\n", (long long)result);
    lua_close(L);
    return 0;
}
