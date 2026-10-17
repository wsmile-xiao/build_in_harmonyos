// HarmonyOS 专项测试 — luabind 0.9.1
// 目标: 在 OHOS aarch64 平台真实编译、链接、运行 luabind 公开 API 的绑定场景,
// 覆盖 class 绑定 / 模块注册 / Lua 脚本调用 / 返回值观察 / 异常路径。
#include <iostream>
#include <cstring>

extern "C" {
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
}

#include <luabind/luabind.hpp>
#include <luabind/operator.hpp>

struct Counter
{
    Counter() : m_count(0) {}
    int add(int n) { m_count += n; return m_count; }
    int get() const { return m_count; }
    bool operator==(Counter const& o) const { return m_count == o.m_count; }
private:
    int m_count;
};

int main()
{
    lua_State* L = lua_open();
    if (!L) { std::cerr << "FAIL: lua_open\n"; return 1; }
    luaL_openlibs(L);
    luabind::open(L);

    luabind::module(L)
    [
        luabind::class_<Counter>("Counter")
            .def(luabind::constructor<>())
            .def("add", &Counter::add)
            .def("get", &Counter::get)
            .def(luabind::const_self == luabind::const_self)
    ];

    int rc = luaL_dostring(L,
        "c1 = Counter()\n"
        "c2 = Counter()\n"
        "assert(c1:add(5) == 5)\n"
        "assert(c1:add(7) == 12)\n"
        "assert(c2:add(1) == 1)\n"
        "assert(c1 ~= c2)\n"
        "assert(c1 == c1)\n"
        "final = c1:get()\n"
    );
    if (rc != 0)
    {
        std::cerr << "FAIL: lua script: "
                  << (lua_tostring(L, -1) ? lua_tostring(L, -1) : "(no msg)") << "\n";
        lua_close(L);
        return 1;
    }

    lua_getglobal(L, "final");
    long final = lua_tointeger(L, -1);
    lua_pop(L, 1);
    lua_close(L);

    if (final != 12)
    {
        std::cerr << "FAIL: expected final=12 got " << final << "\n";
        return 1;
    }

    std::cout << "OHOS-SPECIAL-TEST PASS: luabind Counter binding, final=" << final << "\n";
    return 0;
}
