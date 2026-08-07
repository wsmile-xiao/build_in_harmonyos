#include <stdio.h>
#include <stdlib.h>

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

    const char *lua_path = getenv("LUA_PATH");
    if (lua_path != NULL) {
        lua_getglobal(L, "package");
        lua_pushstring(L, lua_path);
        lua_setfield(L, -2, "path");
        lua_pop(L, 1);
    }

    const char *script =
        "local Mediator = require('mediator')\n"
        "assert(type(Mediator) == 'table')\n"
        "local mediator = Mediator()\n"
        "local received\n"
        "local sub = mediator:subscribe({'ohos'}, function(payload) received = payload.value end)\n"
        "assert(type(sub.id) == 'number')\n"
        "mediator:publish({'ohos'}, {value = 'ok'})\n"
        "assert(received == 'ok')\n"
        "assert(mediator:getSubscriber(sub.id, {'ohos'}).value == sub)\n"
        "mediator:removeSubscriber(sub.id, {'ohos'})\n"
        "assert(mediator:getSubscriber(sub.id, {'ohos'}) == nil)\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "%s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    puts("mediator_lua smoke ok");
    return 0;
}

