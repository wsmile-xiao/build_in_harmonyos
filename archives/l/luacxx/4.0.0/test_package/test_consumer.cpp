// Consumer validation test for luacxx 4.0.0.
//
// This consumer simulates an upper-layer business component: it uses ONLY the
// public headers and API exported by the installed luacxx package, links the
// installed library, and verifies a real public-API round trip:
//   1. Lua state creation via lua::create()
//   2. C++ <-> Lua value conversion (lua::push / lua::get)
//   3. Registering a C++ function and calling it from a Lua script
//   4. Table / global access through the public index API
#include <cstdio>
#include <cstring>
#include <string>

#include <luacxx/stack.hpp>
#include <luacxx/algorithm.hpp>
#include <luacxx/thread.hpp>
#include <luacxx/load.hpp>
#include <luacxx/convert/callable.hpp>
#include <luacxx/convert/const_char_p.hpp>
#include <luacxx/convert/string.hpp>
#include <luacxx/convert/numeric.hpp>

int main()
{
    int failures = 0;

    // 1. Create a Lua state.
    auto env = lua::create();
    std::printf("[consumer] lua::create() ok\n");

    // 2. Value round trip: push an int, read it back.
    env << 7;
    const int seven = lua::get<int>(env, 1);
    std::printf("[consumer] pushed/retrieved int: %d\n", seven);
    if (seven != 7) { failures++; }

    // 3. String conversion through the public API.
    env << "score=42";
    const char* s = lua::get<const char*>(env, 2);
    std::printf("[consumer] pushed/retrieved string: %s\n", s);
    if (std::strcmp(s, "score=42") != 0) { failures++; }

    // 4. Register a C++ function, call it from a Lua script (round trip).
    env["multiply"] = lua::push_function<int(int, int)>(
        env, [](int a, int b) { return a * b; });
    const int product = lua::run_string<int>(env, "return multiply(6, 7)");
    std::printf("[consumer] lua->c++ round trip multiply(6,7) = %d\n", product);
    if (product != 42) { failures++; }

    // 5. Table through the public index API.
    env["cfg"] = lua::value::table;
    env["cfg"]["mode"] = "consumer";
    const std::string mode = lua::get<std::string>(env["cfg"]["mode"]);
    std::printf("[consumer] table lookup cfg.mode = %s\n", mode.c_str());
    if (mode != "consumer") { failures++; }

    std::printf("[consumer] %s (%d failure%s)\n",
                failures == 0 ? "PASSED" : "FAILED",
                failures,
                failures == 1 ? "" : "s");
    return failures == 0 ? 0 : 1;
}