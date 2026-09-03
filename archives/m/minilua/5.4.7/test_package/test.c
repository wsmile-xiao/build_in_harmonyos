#include <stdio.h>
#include <string.h>

#define LUA_IMPL
#include <minilua.h>

static int verify_condition(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void) {
    int failures = 0;
    lua_State *state = luaL_newstate();
    failures += verify_condition(state != NULL, "luaL_newstate");
    if (state == NULL) {
        return failures;
    }

    luaL_openlibs(state);
    int status = luaL_loadstring(state, "return 2 + 3, 'minilua'");
    failures += verify_condition(status == LUA_OK, "luaL_loadstring");
    if (status == LUA_OK) {
        status = lua_pcall(state, 0, 2, 0);
    }
    failures += verify_condition(status == LUA_OK, "lua_pcall");
    failures += verify_condition(lua_gettop(state) == 2, "two Lua return values");
    failures += verify_condition(lua_tointeger(state, -2) == 5, "integer result");

    size_t length = 0;
    const char *text = lua_tolstring(state, -1, &length);
    failures += verify_condition(
        text != NULL && length == 7 && strcmp(text, "minilua") == 0,
        "string result");

    lua_close(state);
    if (failures == 0) {
        puts("minilua 5.4.7 consumer: 6 assertions passed");
    }
    return failures;
}
