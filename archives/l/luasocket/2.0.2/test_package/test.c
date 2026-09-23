/*
 * Consumer test for luasocket 2.0.2 (Lua 5.1).
 *
 * Embeds a Lua 5.1 interpreter, configures package.path / package.cpath to
 * locate the installed luasocket modules, then runs a Lua script that
 * requires "socket", "mime", "socket.url", "ltn12" and "socket.http" and
 * exercises their APIs: TCP socket creation/close, DNS gethostname,
 * MIME base64 round-trip, URL parse/build.
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

    /* Set package.cpath so Lua can find socket/core.so and mime/core.so. */
    snprintf(buf, sizeof(buf),
        "package.cpath = '%s/lib/lua/5.1/?.so;' .. package.cpath", pkg);
    if (luaL_dostring(L, buf) != 0) {
        fprintf(stderr, "set cpath failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    /* Set package.path so Lua can find socket.lua, mime.lua, ltn12.lua,
     * socket/url.lua, socket/http.lua, etc. */
    snprintf(buf, sizeof(buf),
        "package.path = '%s/share/lua/5.1/?.lua;' .. package.path", pkg);
    if (luaL_dostring(L, buf) != 0) {
        fprintf(stderr, "set path failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    const char *script =
        "local socket = require('socket')\n"
        "local mime = require('mime')\n"
        "local url = require('socket.url')\n"
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
        /* UDP socket creation */
        "local us = socket.udp()\n"
        "assert(us, 'failed to create UDP socket')\n"
        "assert(us:close(), 'failed to close UDP socket')\n"
        /* DNS lookup exercises inet / usocket paths */
        "local hostname = socket.dns.gethostname()\n"
        "assert(hostname and #hostname > 0, 'failed to get hostname')\n"
        /* MIME round-trip */
        "local encoded = mime.b64('hello')\n"
        "assert(encoded, 'mime.b64 returned nil')\n"
        "local decoded = mime.unb64(encoded)\n"
        "assert(decoded == 'hello', 'mime round-trip mismatch')\n"
        /* URL parse/build (2.0.2: port is a string, url is standalone) */
        "local u = url.parse('http://user:pass@host:8080/path?q=1#frag')\n"
        "assert(u.host == 'host', 'url parse: host mismatch')\n"
        "assert(tonumber(u.port) == 8080, 'url parse: port mismatch')\n"
        "assert(u.user == 'user' and u.password == 'pass', 'url parse: userinfo mismatch')\n"
        "assert(u.path == '/path' and u.query == 'q=1' and u.fragment == 'frag', 'url parse: path/query mismatch')\n"
        "local rebuilt = url.build(u)\n"
        "assert(type(rebuilt) == 'string' and #rebuilt > 0, 'url build failed')\n"
        /* ltn12 and socket.http load paths */
        "local ltn12 = require('ltn12')\n"
        "assert(type(ltn12.pump) == 'table' and type(ltn12.pump.all) == 'function', 'ltn12 missing')\n"
        "local http = require('socket.http')\n"
        "assert(type(http.request) == 'function', 'socket.http missing')\n"
        "print('luasocket 2.0.2 consumer test passed: '\n"
        "  .. tostring(socket._VERSION) .. ' / ' .. tostring(mime._VERSION))\n";

    if (luaL_dostring(L, script) != 0) {
        const char *err = lua_tostring(L, -1);
        fprintf(stderr, "Lua test failed: %s\n",
                err ? err : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
