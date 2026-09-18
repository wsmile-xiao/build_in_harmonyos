/* Functional consumer and HarmonyOS loader test for libmpack-lua. */
#include <dlfcn.h>
#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(__OHOS__) || defined(__OHOS)
#include <sys/stat.h>
#include <sys/utsname.h>
#endif

static int run_lua_contract(lua_State *state)
{
    static const char script[] =
        "local mpack = assert(require('mpack'))\n"
        "assert(type(mpack.pack) == 'function')\n"
        "assert(type(mpack.unpack) == 'function')\n"
        "local blob = mpack.pack({payload='openharmony', values={1, true, mpack.NIL}})\n"
        "local value = assert(mpack.unpack(blob))\n"
        "assert(value.payload == 'openharmony')\n"
        "assert(value.values[1] == 1 and value.values[2] == true)\n"
        "assert(value.values[3] == mpack.NIL)\n"
        "local binary = mpack.Packer({is_bin=true})('abc')\n"
        "assert(string.byte(binary, 1) == 196)\n"
        "local session = mpack.Session()\n"
        "assert(session:request('method') == string.char(148, 0, 0))\n"
        "local kind, id, position = session:receive(string.char(148, 0, 0))\n"
        "assert(kind == 'request' and id == 0 and position == 4)\n"
        "assert(tostring(mpack.NIL) == 'mpack.NIL')\n";

    if (luaL_dostring(state, script) != 0) {
        fprintf(stderr, "Lua libmpack contract failed: %s\n",
                lua_tostring(state, -1));
        return 0;
    }
    return 1;
}

static int configure_module_path(lua_State *state, const char *module)
{
    lua_getglobal(state, "package");
    if (!lua_istable(state, -1)) {
        fprintf(stderr, "Lua package table is unavailable\n");
        lua_pop(state, 1);
        return 0;
    }
    lua_pushstring(state, module);
    lua_setfield(state, -2, "cpath");
    lua_pop(state, 1);
    return 1;
}

int main(int argc, char **argv)
{
    int checks = 0;
    const char *module;
    void *handle;
    void *entry;
    lua_State *state;

    if (argc != 2) {
        fprintf(stderr, "usage: %s /path/to/mpack.so\n", argv[0]);
        return 2;
    }
    module = argv[1];

    handle = dlopen(module, RTLD_NOW | RTLD_GLOBAL);
    if (handle == NULL) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", module, dlerror());
        return 3;
    }
    checks++;

    entry = dlsym(handle, "luaopen_mpack");
    if (entry == NULL) {
        fprintf(stderr, "dlsym(luaopen_mpack) failed: %s\n", dlerror());
        dlclose(handle);
        return 4;
    }
    checks++;

#if defined(__OHOS__) || defined(__OHOS)
    {
        struct stat module_stat;
        struct utsname system_info;

        if (stat(module, &module_stat) != 0 || !S_ISREG(module_stat.st_mode)) {
            fprintf(stderr, "OHOS module path is not a regular file: %s\n", module);
            dlclose(handle);
            return 5;
        }
        if (uname(&system_info) != 0 || system_info.sysname[0] == '\0') {
            fprintf(stderr, "OHOS uname check failed\n");
            dlclose(handle);
            return 6;
        }
        printf("harmonyos_specific_test: __OHOS__ defined, sysname=%s\n",
               system_info.sysname);
        checks += 2;
    }
#else
    printf("harmonyos_specific_test: host build (OHOS branch compiled on target)\n");
#endif

    state = luaL_newstate();
    if (state == NULL) {
        fprintf(stderr, "luaL_newstate failed\n");
        dlclose(handle);
        return 7;
    }
    luaL_openlibs(state);
    if (!configure_module_path(state, module)) {
        lua_close(state);
        dlclose(handle);
        return 8;
    }
    if (!run_lua_contract(state)) {
        lua_close(state);
        dlclose(handle);
        return 9;
    }
    checks += 4;

    lua_close(state);
    dlclose(handle);
    printf("libmpack-lua consumer checks=%d passed\n", checks);
    return 0;
}
