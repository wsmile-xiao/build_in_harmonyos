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

    /* Set package.path from LUA_PATH env so require("mimetypes") works */
    const char *lua_path = getenv("LUA_PATH");
    if (lua_path != NULL) {
        lua_getglobal(L, "package");
        lua_pushstring(L, lua_path);
        lua_setfield(L, -2, "path");
        lua_pop(L, 1);
    }

    const char *script =
        "local mimetypes = require('mimetypes')\n"
        /* Test version */
        "assert(mimetypes.version == '1.0.0', 'version mismatch: ' .. tostring(mimetypes.version))\n"
        /* Test basic extension guessing */
        "assert(mimetypes.guess('memo.doc') == 'application/msword')\n"
        "assert(mimetypes.guess('rickroll.mp3') == 'audio/mpeg')\n"
        "assert(mimetypes.guess('cat.png') == 'image/png')\n"
        "assert(mimetypes.guess('forwarded.eml') == 'message/rfc822')\n"
        "assert(mimetypes.guess('docs.txt') == 'text/plain')\n"
        "assert(mimetypes.guess('init.lua') == 'text/x-lua')\n"
        "assert(mimetypes.guess('fish.mpg') == 'video/mpeg')\n"
        "assert(mimetypes.guess('notareal.mimetype') == nil)\n"
        /* Test special filenames */
        "assert(mimetypes.guess('README') == 'text/plain')\n"
        "assert(mimetypes.guess('Makefile') == 'text/x-makefile')\n"
        "assert(mimetypes.guess('NINJAS') == nil)\n"
        /* Test detecting extensions */
        "assert(mimetypes.guess('txt') == nil)\n"
        "assert(mimetypes.guess('mimetypes-1.0.tar.gz') == 'application/x-gzip')\n"
        /* Test copying MIME types */
        "local db = mimetypes.copy()\n"
        "db.extensions.xmp = 'application/x-example'\n"
        "assert(mimetypes.guess('file.xmp', db) == 'application/x-example')\n"
        "assert(mimetypes.guess('file.xmp') == nil)\n"
        "print('All tests passed')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "Lua test failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 2;
    }

    lua_close(L);
    return 0;
}
