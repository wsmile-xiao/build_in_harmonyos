/* test_package/test.cpp - chaiscript 6.1.0 consumer test
   Verifies <chaiscript/chaiscript.hpp> compiles, links and runs:
   - eval expressions (int/string) return correct values
   - registering a C++ function and calling it from script (embedding API)
   - script variables / loops / recursive functions (language features)
   - Std_Lib vector map operator (bootstrap_stl)
   - eval_error exception path
   - multi-threaded concurrent eval on a shared engine (threading locks)
   Upstream ships 234 .chai + 10 .cpp tests in unittests/ (Catch framework
   is fetched from the network at build time; see notes.md for the trim
   rationale). This is a supplementary consumer-side test.
   ASCII-only comments on purpose: MSVC reads sources as CP936 by default.
*/
#include <chaiscript/chaiscript.hpp>
#include <atomic>
#include <cstdio>
#include <string>
#include <thread>

static int g_failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (cond) {                                                     \
            std::printf("PASS: %s\n", #cond);                           \
        } else {                                                        \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);       \
            ++g_failures;                                               \
        }                                                               \
    } while (0)

static int triple(int x) {
    return 3 * x;
}

int main() {
    chaiscript::ChaiScript chai;

    // 1. basic arithmetic eval
    CHECK(chai.eval<int>("40 + 2") == 42);

    // 2. string eval
    CHECK(chai.eval<std::string>("\"hello\" + \" \" + \"chaiscript\"")
          == "hello chaiscript");

    // 3. register a C++ function, call it from script
    chai.add(chaiscript::fun(&triple), "triple");
    CHECK(chai.eval<int>("triple(14)") == 42);

    // 4. script variable + for loop (block eval yields last value)
    CHECK(chai.eval<int>(
        "var fact = 1;"
        "for (var i = 1; i <= 6; ++i) { fact *= i; }"
        "fact") == 720);

    // 5. recursive function definition
    CHECK(chai.eval<int>(
        "def fib(n) {"
        "  if (n < 2) { return n; }"
        "  fib(n - 1) + fib(n - 2)"
        "}"
        "fib(15)") == 610);

    // 6. Std_Lib: vector literal + map operator
    CHECK(chai.eval<int>("var v = [1, 2, 3, 4];"
                         "v.map(fun(x) { x * x })[3]") == 16);

    // 7. eval_error exception path
    bool caught = false;
    try {
        chai.eval("this is !!! not valid chai");
    } catch (const chaiscript::exception::eval_error &) {
        caught = true;
    }
    CHECK(caught);

    // 8. concurrent eval on a shared engine (threading locks + thread_local)
    {
        std::atomic<int> thread_failures{0};
        auto worker = [&chai, &thread_failures](int base) {
            for (int i = 0; i < 32; ++i) {
                try {
                    if (chai.eval<int>(std::to_string(base) + " * 2")
                        != base * 2) {
                        ++thread_failures;
                    }
                } catch (...) {
                    ++thread_failures;
                }
            }
        };
        std::thread t1(worker, 21);
        std::thread t2(worker, 100);
        t1.join();
        t2.join();
        CHECK(thread_failures.load() == 0);
    }

    if (g_failures == 0) {
        std::printf("chaiscript smoke test: ALL PASS\n");
        return 0;
    }
    std::printf("chaiscript smoke test: %d FAILURE(S)\n", g_failures);
    return 1;
}
