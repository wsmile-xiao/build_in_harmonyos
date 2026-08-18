#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
#include <stdio.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "Failed to create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);
    if (luaL_dostring(L, "print('Hello from LuaJIT!')") != LUA_OK) {
        fprintf(stderr, "Failed to run Lua: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }
    lua_close(L);
    printf("LuaJIT test: OK\n");
    return 0;
}
