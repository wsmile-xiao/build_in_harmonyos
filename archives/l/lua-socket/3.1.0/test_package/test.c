/*
 * Consumer test for lua-socket.
 *
 * Embeds a Lua interpreter, configures package.path / package.cpath to
 * locate the installed lua-socket modules, then runs a Lua script that
 * requires "socket" and "mime" and exercises core APIs.
 */
#include <lauxlib.h>
#include <lualib.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <package_folder>\n", argv[0]);
        return 1;
    }
    const char *pkg = argv[1];

    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "failed to create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    char buf[2048];

    /* Set package.cpath so Lua can find socket/core.so, mime/core.so, etc. */
    snprintf(buf, sizeof(buf),
        "package.cpath = '%s/lib/lua/5.4/?.so;' .. package.cpath", pkg);
    if (luaL_dostring(L, buf) != LUA_OK) {
        fprintf(stderr, "set cpath failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* Set package.path so Lua can find socket.lua, mime.lua, ltn12.lua, etc. */
    snprintf(buf, sizeof(buf),
        "package.path = '%s/share/lua/5.4/?.lua;%s/share/lua/5.4/?/init.lua;' .. package.path",
        pkg, pkg);
    if (luaL_dostring(L, buf) != LUA_OK) {
        fprintf(stderr, "set path failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    const char *script =
        "local socket = require('socket')\n"
        "local mime = require('mime')\n"
        "assert(type(socket) == 'table', 'socket is not a table')\n"
        "assert(type(mime) == 'table', 'mime is not a table')\n"
        "assert(type(socket.tcp) == 'function', 'socket.tcp is not a function')\n"
        "assert(type(socket.udp) == 'function', 'socket.udp is not a function')\n"
        "assert(type(socket.dns) == 'table', 'socket.dns is not a table')\n"
        "assert(type(mime.b64) == 'function', 'mime.b64 is not a function')\n"
        "assert(type(mime.unb64) == 'function', 'mime.unb64 is not a function')\n"
        /* Create and immediately close a TCP socket to exercise the C API */
        "local s = socket.tcp()\n"
        "assert(s, 'failed to create TCP socket')\n"
        "assert(s:close(), 'failed to close TCP socket')\n"
        /* DNS lookup exercises inet / usocket paths */
        "local hostname = socket.dns.gethostname()\n"
        "assert(hostname and #hostname > 0, 'failed to get hostname')\n"
        /* MIME round-trip */
        "local encoded = mime.b64('hello')\n"
        "assert(encoded, 'mime.b64 returned nil')\n"
        "local decoded = mime.unb64(encoded)\n"
        "assert(decoded == 'hello', 'mime round-trip mismatch')\n"
        "print('lua-socket consumer test passed')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        const char *err = lua_tostring(L, -1);
        fprintf(stderr, "Lua test failed: %s\n",
                err ? err : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
