#include <stdio.h>

#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

static void set_arg_table(lua_State *L, int argc, char **argv) {
    lua_createtable(L, argc, 1);
    for (int i = 0; i < argc; ++i) {
        lua_pushstring(L, argv[i]);
        lua_rawseti(L, -2, i);
    }
    lua_setglobal(L, "arg");
}

static int apply_lua_cli_arg_compat(lua_State *L) {
    const char *script =
        "do\n"
        "  local lua = os.getenv('BUSTED_LUA')\n"
        "  if not lua or lua == '' then lua = 'lua' end\n"
        "  arg[-3] = lua\n"
        "  arg[-2] = '-e'\n"
        "  arg[-1] = ('package.path=%q;package.cpath=%q;local _busted_launcher=true'):format(package.path, package.cpath)\n"
        "end\n";
    return luaL_dostring(L, script);
}

static int apply_tmpdir_tmpname(lua_State *L) {
    const char *script =
        "do\n"
        "  local tmpdir = os.getenv('TMPDIR')\n"
        "  if tmpdir and tmpdir ~= '' then\n"
        "    local counter = 0\n"
        "    local token = tostring({}):gsub('[^%w]', '')\n"
        "    os.tmpname = function()\n"
        "      counter = counter + 1\n"
        "      return tmpdir .. '/lua_' .. token .. '_' .. tostring(counter) .. '.tmp'\n"
        "    end\n"
        "    local original_tmpfile = io.tmpfile\n"
        "    io.tmpfile = function()\n"
        "      local handle, err, code = original_tmpfile()\n"
        "      if handle then return handle end\n"
        "      local name = os.tmpname()\n"
        "      handle, err, code = io.open(name, 'w+')\n"
        "      if not handle then return nil, err, code end\n"
        "      os.remove(name)\n"
        "      return handle\n"
        "    end\n"
        "  end\n"
        "end\n";
    return luaL_dostring(L, script);
}

int main(int argc, char **argv) {
    lua_State *L = luaL_newstate();
    if (L == NULL) {
        fputs("busted: failed to create Lua state\n", stderr);
        return 1;
    }

    luaL_openlibs(L);
    set_arg_table(L, argc, argv);

    if (apply_lua_cli_arg_compat(L) != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "busted: %s\n", message != NULL ? message : "failed to initialize Lua CLI arg compatibility");
        lua_close(L);
        return 1;
    }

    if (apply_tmpdir_tmpname(L) != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "busted: %s\n", message != NULL ? message : "failed to initialize tmpname override");
        lua_close(L);
        return 1;
    }

    /*
     * Keep this as a plain statement. Returning the call would turn it into a
     * tail call and remove the Lua frame that busted.runner inspects via
     * debug.getinfo(2, ...).
     */
    int status = luaL_dostring(L, "require('busted.runner')({ standalone = false })");
    if (status != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "busted: %s\n", message != NULL ? message : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    int exit_code = 0;
    if (lua_isinteger(L, -1)) {
        exit_code = (int)lua_tointeger(L, -1);
    } else if (lua_isboolean(L, -1)) {
        exit_code = lua_toboolean(L, -1) ? 0 : 1;
    }

    lua_close(L);
    return exit_code;
}
