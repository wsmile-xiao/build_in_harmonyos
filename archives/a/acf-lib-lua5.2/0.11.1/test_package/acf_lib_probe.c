#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int set_module_path(lua_State *state, const char *root) {
    size_t length = strlen(root) * 2 + 32;
    char *path = (char *)malloc(length);
    if (path == NULL) {
        return 0;
    }
    snprintf(path, length, "%s/?.lua;%s/?/init.lua", root, root);
    lua_getglobal(state, "package");
    if (!lua_istable(state, -1)) {
        free(path);
        lua_pop(state, 1);
        return 0;
    }
    lua_pushstring(state, path);
    lua_setfield(state, -2, "path");
    lua_pop(state, 1);
    free(path);
    return 1;
}

static int run_chunk(lua_State *state, const char *chunk, const char *scenario) {
    if (luaL_dostring(state, chunk) != LUA_OK) {
        fprintf(stderr, "FAIL: %s: %s\n", scenario, lua_tostring(state, -1));
        return 0;
    }
    if (!lua_toboolean(state, -1)) {
        fprintf(stderr, "FAIL: %s returned false\n", scenario);
        lua_pop(state, 1);
        return 0;
    }
    lua_pop(state, 1);
    return 1;
}

int main(int argc, char **argv) {
    static const char positive[] =
        "local format = require('acf.format')\n"
        "local html = require('acf.html')\n"
        "local validator = require('acf.validator')\n"
        "assert(format.dostounix('one\\r\\ntwo\\r\\n') == 'one\\ntwo\\n')\n"
        "local lines = format.parse_lines('# ignored\\nalpha\\n\\n beta\\n')\n"
        "assert(#lines == 2 and lines[1] == 'alpha' and lines[2] == ' beta')\n"
        "assert(html.html_escape('<a&>') == '&lt;a&amp;&gt;')\n"
        "assert(html.html_escape('\"') == '&quot;')\n"
        "assert(html.html_escape(\"'\") == '&#39;')\n"
        "assert(html.url_encode('a b/c') == 'a+b%2Fc')\n"
        "assert(validator.is_ipv4('192.168.1.20'))\n"
        "assert(validator.is_port('65535'))\n"
        "-- Lua 5.2 generic-for control variables are mutable, so the three\n"
        "-- functions patched for Lua 5.5 run unmodified here.\n"
        "local ini = '# c\\n[a]\\nb=c\\n'\n"
        "local upd = format.update_ini_file(ini, 'a', 'b', 'v2')\n"
        "assert(upd:find('b=v2', 1, true) ~= nil, 'update_ini_file')\n"
        "assert(format.parse_ini_file(ini, 'a', 'b') == 'c', 'parse_ini_file')\n"
        "local sect = format.set_ini_section(ini, 'a', 'x=1\\ny=2')\n"
        "assert(sect:find('x=1', 1, true) ~= nil, 'set_ini_section')\n"
        "local compat = require('format')\n"
        "assert(compat.dostounix('x\\r') == 'x')\n"
        "return true\n";
    static const char invalid[] =
        "local validator = require('acf.validator')\n"
        "local valid, reason = validator.is_ipv4('999.2.3.4')\n"
        "assert(not valid and reason == 'Invalid Value')\n"
        "assert(not validator.is_port('65536'))\n"
        "return true\n";

    int invalid_mode = argc == 3 && strcmp(argv[1], "--expect-invalid") == 0;
    const char *root = invalid_mode ? argv[2] : (argc == 2 ? argv[1] : NULL);
    if (root == NULL) {
        fprintf(stderr, "usage: acf_lib_probe [--expect-invalid] <lua-module-root>\n");
        return 2;
    }

    lua_State *state = luaL_newstate();
    if (state == NULL) {
        fprintf(stderr, "FAIL: cannot create Lua state\n");
        return 1;
    }
    luaL_openlibs(state);
    if (!set_module_path(state, root)) {
        fprintf(stderr, "FAIL: cannot set package.path\n");
        lua_close(state);
        return 1;
    }

    int passed = run_chunk(
        state,
        invalid_mode ? invalid : positive,
        invalid_mode ? "invalid-input rejection" : "packaged-module API checks"
    );
    lua_close(state);
    if (!passed) {
        return 1;
    }
    printf(
        "PASS: %s\n",
        invalid_mode ? "invalid IPv4 and port rejected" : "packaged Lua modules invoked"
    );
    return 0;
}
