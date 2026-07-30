#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lua.h"
#include "luacode.h"
#include "lualib.h"

int main(void)
{
    lua_State* L = luaL_newstate();
    if (L == NULL)
    {
        fprintf(stderr, "Failed to create luau state\n");
        return 1;
    }

    luaL_openlibs(L);

    const char* code = "local x = 1 + 1; return x";
    size_t code_len = strlen(code);
    size_t bytecode_len = 0;
    char* bytecode = luau_compile(code, code_len, NULL, &bytecode_len);
    if (bytecode == NULL || bytecode_len == 0)
    {
        fprintf(stderr, "Failed to compile luau code\n");
        free(bytecode);
        lua_close(L);
        return 1;
    }

    int load_result = luau_load(L, "test_chunk", bytecode, bytecode_len, 0);
    free(bytecode);
    if (load_result != 0)
    {
        fprintf(stderr, "Failed to load luau code\n");
        lua_close(L);
        return 1;
    }

    int call_result = lua_pcall(L, 0, 1, 0);
    if (call_result != 0)
    {
        fprintf(stderr, "Failed to execute luau code\n");
        lua_close(L);
        return 1;
    }

    if (!lua_isnumber(L, -1))
    {
        fprintf(stderr, "Expected number result\n");
        lua_close(L);
        return 1;
    }

    double value = lua_tonumber(L, -1);
    if (value < 1.99 || value > 2.01)
    {
        fprintf(stderr, "Expected 2.0, got %f\n", value);
        lua_close(L);
        return 1;
    }

    lua_close(L);
    printf("test luau 0.689: OK\n");
    return 0;
}
