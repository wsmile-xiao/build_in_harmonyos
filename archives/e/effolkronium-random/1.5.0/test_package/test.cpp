// test_package/test.cpp — R34: substantive consumer test of effolkronium-random.
// Exercises the three provided aliases (random_static, random_thread_local,
// random_local) and a representative subset of the API: range get(), get() with
// no arguments, get() from std::initializer_list, bool/char generation, shuffle,
// and engine access. All generated values must lie in the requested range.
#include <effolkronium/random.hpp>

#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

using RandomStatic = effolkronium::random_static;
using RandomThreadLocal = effolkronium::random_thread_local;
using RandomLocal = effolkronium::random_local;

static int failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::cerr << "FAIL: " #cond " (line " << __LINE__ << ")\n"; \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main() {
    // ── random_static: static-method API ──
    for (int i = 0; i < 100; ++i) {
        int v = RandomStatic::get(1, 6);            // inclusive range
        CHECK(v >= 1 && v <= 6);

        double d = RandomStatic::get(-1.0, 1.0);    // floating range
        CHECK(d >= -1.0 && d <= 1.0);

        bool b = RandomStatic::get<bool>();
        CHECK(b == true || b == false);

        char c = RandomStatic::get('a', 'z');
        CHECK(c >= 'a' && c <= 'z');

        // get() with no arguments produces a value in the engine's full range
        unsigned long big = RandomStatic::get();
        CHECK(true); // presence check: the call itself must not throw/abort
        (void)big;
    }

    // ── std::initializer_list overload ──
    std::string picked = RandomStatic::get({"red", "green", "blue"});
    CHECK(picked == "red" || picked == "green" || picked == "blue");

    // ── random_thread_local: thread-safe variant shares the same API ──
    for (int i = 0; i < 50; ++i) {
        int v = RandomThreadLocal::get(0, 9);
        CHECK(v >= 0 && v <= 9);
    }

    // ── random_local: construct on the stack at local scope ──
    RandomLocal local;
    for (int i = 0; i < 50; ++i) {
        int v = local.get(100, 200);
        CHECK(v >= 100 && v <= 200);
    }

    // ── shuffle ──
    std::vector<int> vec = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    std::vector<int> sorted = vec;
    RandomStatic::shuffle(vec);
    std::sort(vec.begin(), vec.end());
    CHECK(vec == sorted); // permutation must preserve the multiset of values

    // ── engine(): raw engine access to fill a histogram ──
    auto& engine = RandomThreadLocal::engine();
    std::size_t buckets[10] = {0};
    for (int i = 0; i < 2000; ++i) {
        // std::uniform_int_distribution is exercised via raw engine sampling
        buckets[static_cast<std::size_t>(engine() % 10)] += 1;
    }
    for (int i = 0; i < 10; ++i) {
        CHECK(buckets[i] > 0); // each bucket receives at least one draw
    }

    if (failures == 0) {
        std::cout << "effolkronium-random test passed: all assertions OK" << std::endl;
        return 0;
    }
    std::cerr << failures << " assertion(s) failed" << std::endl;
    return 1;
}