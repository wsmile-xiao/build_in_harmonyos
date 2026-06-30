# luv

Bare libuv bindings for Lua.

## Description

luv provides bare libuv bindings for LuaJIT and Lua 5.1/5.2/5.3/5.4. This library makes libuv available to Lua scripts. It was made for the luvit project but should be usable from nearly any Lua project.

## Features

- libuv bindings for Lua
- Support for LuaJIT and PUC Lua 5.1-5.4
- Event-driven I/O
- TCP/UDP sockets
- File system operations
- Timer and signal handling
- Process management

## HarmonyOS Adaptation

luv requires libuv as a dependency. The bundled libuv version has been patched to work on HarmonyOS:

- Disabled CPU affinity features (CPU_SETSIZE, sched_getaffinity)
- Disabled recvmmsg/sendmmsg (mmsghdr structure not available)
- Disabled pthread_setname_np/pthread_getname_np (not available)
- Using PUC Lua instead of LuaJIT (LuaJIT has architecture detection issues on HarmonyOS)

## Version

- 1.51.0-1

## Links

- GitHub: https://github.com/luvit/luv
- libuv: https://github.com/libuv/libuv

## Build Options

- `WITH_LUA_ENGINE=Lua` - Use PUC Lua instead of LuaJIT
- `BUILD_MODULE=OFF` - Build as static library
- `BUILD_STATIC_LIBS=ON` - Build static library

## Usage

### Prerequisites

luv requires the following dependencies to link:

1. **libuv** - Asynchronous I/O library (v1.51.0+)
2. **Lua 5.4+** - Lua interpreter (v5.4+ required, Lua 5.3 not supported)

### Linking

```bash
clang -o myapp myapp.c \
  -I/usr/local/include/luv \
  -L/usr/local/lib \
  -lluv -llua54 -luv -lm -ldl -lpthread
```

### Example Code

```lua
local uv = require('luv')

-- Create a timer
local timer = uv.new_timer()
uv.timer_start(timer, 1000, 0, function()
  print("Timer fired!")
  uv.timer_stop(timer)
  uv.close(timer)
end)

-- Run event loop
uv.run()
```

## Testing

- Test Date: 2026-06-05 (初版) → 2026-06-08 (修复版)
- Test Result: ✅ PASS
- Test Report: `archives/l/luv/1.51.0-1/reports/test-report.md`

### Test Summary

- ✅ Package integrity: PASS
- ✅ Static library format: PASS (ELF64 ARM64)
- ✅ Symbol export: PASS (luaopen_luv available)
- ✅ Platform adaptation: PASS (__OHOS__ guards correct)
- ✅ Quality gates G1-G4: PASS
- ✅ **Linking test: PASS** - libuv 完整编译后可独立链接
- ✅ **Functional test: PASS** - uv.version() = 78592 (libuv v1.51.0)

### Linking Test Success

After fixing libuv CMakeLists.txt to load Linux platform sources, luv can now be linked independently:

```c
// C test program
#include <lua.h>
#include <lauxlib.h>

extern int luaopen_luv(lua_State *L);

int main() {
    lua_State *L = luaL_newstate();
    luaL_openlibs(L);

    // Register luv in package.preload
    lua_getglobal(L, "package");
    lua_getfield(L, -1, "preload");
    lua_pushcfunction(L, luaopen_luv);
    lua_setfield(L, -2, "luv");

    luaL_dostring(L, "local uv = require('luv'); print(uv.version())");
    return 0;
}
```

Result: `uv version: 78592` ✅

## Known Limitations

1. **CPU affinity** - Disabled (cpu_set_t/sched_getaffinity not available)
2. **recvmmsg/sendmmsg** - Disabled (mmsghdr not available)
3. **Thread naming** - Disabled (pthread_setname_np not available)

Core functionality is available:
- TCP/UDP sockets
- File system operations
- Timer and signal handling
- Process management
- Event loop (完整 libuv)