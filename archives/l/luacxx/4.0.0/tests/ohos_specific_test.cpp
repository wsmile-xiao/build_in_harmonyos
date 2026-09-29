// HarmonyOS-specific validation test for luacxx 4.0.0.
// Exercises the public luacxx API against the OHOS aarch64 toolchain and
// the OHOS-built Lua runtime, and asserts real observable results.
#include "luacxx/stack.hpp"
#include "luacxx/algorithm.hpp"
#include "luacxx/convert/callable.hpp"
#include "luacxx/convert/const_char_p.hpp"
#include "luacxx/convert/numeric.hpp"
#include "luacxx/convert/string.hpp"
#include "luacxx/convert/char.hpp"
#include "luacxx/thread.hpp"
#include "luacxx/load.hpp"

#include <cstdio>
#include <string>

namespace {

int ohos_add(lua_State* const state)
{
    auto a = lua::get<int>(state, 1);
    auto b = lua::get<int>(state, 2);
    lua_settop(state, 0);
    lua::push(state, a + b);
    return 1;
}

} // namespace

int main()
{
    int failures = 0;

#if defined(__OHOS__)
    std::printf("[ohos-test] target: OHOS (__OHOS__ defined)\n");
#else
    std::printf("[ohos-test] target: NOT OHOS (__OHOS__ not defined)\n");
    failures++;
#endif

    // 1. Create a Lua state through the public API.
    auto env = lua::create();
    std::printf("[ohos-test] lua::create() ok\n");

    // 2. Push and retrieve native values through the public conversion API.
    env << 42;
    const int v = lua::get<int>(env, 1);
    std::printf("[ohos-test] pushed/retrieved int: %d\n", v);
    if (v != 42) { failures++; }

    env << "no time";
    const char* s = lua::get<const char*>(env, 2);
    std::printf("[ohos-test] pushed/retrieved string: %s\n", s);
    if (std::string(s) != "no time") { failures++; }

    // 3. Register a C++ function and call it from a Lua script (round trip).
    env["add"] = lua::push_function<int(int, int)>(env, [](int a, int b) { return a + b; });
    const int sum = lua::run_string<int>(env, "return add(2, 3)");
    std::printf("[ohos-test] lua->c++->lua round trip add(2,3) = %d\n", sum);
    if (sum != 5) { failures++; }

    // 4. Raw C callback also works on OHOS.
    lua::push(env, ohos_add);
    lua_setglobal(env, "ohos_add");
    const int raw = lua::run_string<int>(env, "return ohos_add(10, 32)");
    std::printf("[ohos-test] raw C callback ohos_add(10,32) = %d\n", raw);
    if (raw != 42) { failures++; }

    // 5. Tables / globals via the public index API.
    env["t"] = lua::value::table;
    env["t"]["k"] = "HarmonyOS";
    const std::string val = lua::get<std::string>(env["t"]["k"]);
    std::printf("[ohos-test] table lookup t.k = %s\n", val.c_str());
    if (val != "HarmonyOS") { failures++; }

    // 6. The OHOS Lua runtime version string is reachable.
    const char* ver = lua::get<const char*>(env, lua_getglobal(env, "_VERSION"));
    lua_pop(env, 1);
    std::printf("[ohos-test] Lua runtime version: %s\n", ver);

    std::printf("[ohos-test] %s (%d failure%s)\n",
                failures == 0 ? "PASSED" : "FAILED", failures, failures == 1 ? "" : "s");
    return failures == 0 ? 0 : 1;
}