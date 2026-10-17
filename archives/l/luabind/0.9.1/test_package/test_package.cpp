// test_package consumer for luabind 0.9.1
// Verifies a third-party consumer can compile, link, call a public luabind
// API (class binding + Lua script invocation) and observe a result.

#include <iostream>
#include <cstring>

extern "C" {
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
}

#include <luabind/luabind.hpp>

struct Greeter
{
    Greeter() : m_count(0) {}
    int increment()
    {
        return ++m_count;
    }
    int count() const
    {
        return m_count;
    }
private:
    int m_count;
};

int main()
{
    lua_State* L = lua_open();
    luaL_openlibs(L);
    luabind::open(L);

    luabind::module(L)
    [
        luabind::class_<Greeter>("Greeter")
            .def(luabind::constructor<>())
            .def("increment", &Greeter::increment)
            .def("count", &Greeter::count)
    ];

    // Call the public API from Lua and observe a real result.
    int rc = luaL_dostring(
        L,
        "g = Greeter()\n"
        "g:increment()\n"
        "g:increment()\n"
        "result = g:count()\n"
    );
    if (rc != 0)
    {
        std::cerr << "lua script failed: "
                  << (lua_tostring(L, -1) ? lua_tostring(L, -1) : "(no message)")
                  << "\n";
        lua_close(L);
        return 1;
    }

    lua_getglobal(L, "result");
    int observed = static_cast<int>(lua_tointeger(L, -1));
    lua_pop(L, 1);
    lua_close(L);

    if (observed != 2)
    {
        std::cerr << "expected count 2, got " << observed << "\n";
        return 1;
    }

    std::cout << "test_package OK: luabind bound Greeter, count=" << observed << "\n";
    return 0;
}