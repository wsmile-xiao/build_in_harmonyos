#include <stdio.h>
#include <string.h>

#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>

#ifndef TABLESHAPE_MODULE_DIR
#error "TABLESHAPE_MODULE_DIR must be defined"
#endif

int main(void)
{
    lua_State *L = luaL_newstate();
    if (L == NULL) {
        fputs("failed to create Lua state\n", stderr);
        return 1;
    }
    luaL_openlibs(L);

    /* Set package.path so require("tableshape") finds the pure-Lua modules. */
    char path[2048];
    snprintf(path, sizeof(path),
             "%s/?.lua;%s/?/init.lua",
             TABLESHAPE_MODULE_DIR, TABLESHAPE_MODULE_DIR);
    lua_getglobal(L, "package");
    lua_pushstring(L, path);
    lua_setfield(L, -2, "path");
    lua_pop(L, 1);

    /* Test core tableshape module */
    const char *code =
        "local ts = assert(require('tableshape'))\n"
        "local types = ts.types\n"
        "assert(type(types) == 'table', 'types should be a table')\n"
        "assert(types.string('hello') == true, 'types.string should match')\n"
        "assert(types.string(42) == nil, 'types.string should reject numbers')\n"
        "assert(types.number(42) == true, 'types.number should match')\n"
        "assert(types.number('hi') == nil, 'types.number should reject strings')\n"
        "assert(types.boolean(true) == true, 'types.boolean should match')\n"
        /* Test shape type */
        "local shape = types.shape{\n"
        "  name = types.string,\n"
        "  age = types.number,\n"
        "}\n"
        "assert(shape({name='John', age=30}) == true, 'shape should match valid input')\n"
        "assert(shape({name='Jane'}) == nil, 'shape should reject missing fields')\n"
        /* Test one_of type */
        "local limbs = types.one_of{'foot', 'arm'}\n"
        "assert(limbs('foot') == true, 'one_of should match')\n"
        "assert(limbs('baseball') == nil, 'one_of should reject')\n"
        /* Test array_of type */
        "local nums = types.array_of(types.number)\n"
        "assert(nums({1,2,3}) == true, 'array_of should match')\n"
        "assert(nums({1,'x',3}) == nil, 'array_of should reject mixed')\n"
        /* Test transform */
        "local t = types.number + types.string / tonumber\n"
        "assert(t:transform('500') == 500, 'transform should coerce string to number')\n"
        "assert(t:transform(5) == 5, 'transform should pass through number')\n"
        /* Test is_type function */
        "assert(ts.is_type(types.string) == true, 'is_type should detect types')\n"
        "assert(ts.is_type('hello') == false, 'is_type should reject non-types')\n"
        /* Test moonscript extension (only depends on tableshape) */
        "local moon = require('tableshape.moonscript')\n"
        "assert(type(moon) == 'table', 'moonscript ext should load')\n"
        "assert(type(moon.class_type) == 'table', 'moonscript should have class_type')\n"
        /* Test with_args extension (only depends on tableshape) */
        "local wa = require('tableshape.ext.with_args')\n"
        "assert(type(wa) == 'table', 'with_args ext should load')\n"
    ;
    if (luaL_dostring(L, code) != LUA_OK) {
        fprintf(stderr, "Lua test failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }
    lua_close(L);
    puts("lua-tableshape consumer test passed");
    return 0;
}
