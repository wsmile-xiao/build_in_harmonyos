#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "Failed to create lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    /* Run a Lua script that computes 2+3 and pushes result */
    if (luaL_dostring(L, "return 2 + 3") != LUA_OK) {
        fprintf(stderr, "Lua error: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* Verify the result is 5 */
    if (!lua_isnumber(L, -1)) {
        fprintf(stderr, "Expected number result\n");
        lua_close(L);
        return 1;
    }
    int result = (int)lua_tointeger(L, -1);
    if (result != 5) {
        fprintf(stderr, "Expected 5, got %d\n", result);
        lua_close(L);
        return 1;
    }

    printf("lua test passed: 2+3=%d\n", result);
    lua_close(L);
    return 0;
}
