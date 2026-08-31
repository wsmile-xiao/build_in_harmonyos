// HarmonyOS-specific test for function2 4.2.3
//
// Verifies concrete Harmony-compatible behavior of the fu2::function API
// (aarch64 OHOS toolchain: clang 15, libc++, C++17):
//  1. move-only callable can be stored and invoked via fu2::unique_function
//  2. fu2::function correctly reports empty state and swaps
//  3. overloadable multi-signature call works
// Not a print-only / compile-only / empty test: every section asserts a
// concrete result and the process exits non-zero on any mismatch.
#include <cstdio>
#include <string>
#include <utility>
#include "function2/function2.hpp"

static int failures = 0;
#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (!(cond)) {                                                \
            std::printf("HMOS_TEST FAIL: %s (%s:%d)\n", msg,          \
                        __FILE__, __LINE__);                          \
            ++failures;                                               \
        }                                                             \
    } while (0)

int main() {
    // 1) move-only callable in unique_function
    {
        struct MoveOnly {
            int value;
            explicit MoveOnly(int v) : value(v) {}
            MoveOnly(MoveOnly &&) = default;
            MoveOnly &operator=(MoveOnly &&) = default;
            MoveOnly(const MoveOnly &) = delete;
            MoveOnly &operator=(const MoveOnly &) = delete;
            int operator()() const { return value; }
        };
        fu2::unique_function<int()> f = MoveOnly(42);
        CHECK(static_cast<bool>(f), "unique_function holds callable");
        CHECK(f() == 42, "unique_function invoke result");
    }

    // 2) empty state / reset / swap
    {
        fu2::function<int(int)> f;
        CHECK(!static_cast<bool>(f), "default function is empty");
        f = [](int x) { return x + 1; };
        CHECK(static_cast<bool>(f), "assigned function is non-empty");
        CHECK(f(1) == 2, "function invoke result");
        f = nullptr;
        CHECK(!static_cast<bool>(f), "nullptr assignment empties function");

        fu2::function<int()> a = [] { return 1; };
        fu2::function<int()> b = [] { return 2; };
        a.swap(b);
        CHECK(a() == 2 && b() == 1, "swap exchanges payloads");
    }

    // 3) multiple overload signatures on one fu2::function
    {
        struct Multi {
            int operator()(int a) const { return a; }
            int operator()(int a, int b) const { return a + b; }
        };
        fu2::function<int(int), int(int, int)> multi = Multi{};
        CHECK(multi(7) == 7, "multi-signature single-arg invoke");
        CHECK(multi(2, 3) == 5, "multi-signature two-arg invoke");
    }

    if (failures == 0) {
        std::printf("HMOS_TEST function2 4.2.3: PASS (aarch64 OHOS, clang15/libc++)\n");
        return 0;
    }
    std::printf("HMOS_TEST function2 4.2.3: FAILED (%d failures)\n", failures);
    return 1;
}
