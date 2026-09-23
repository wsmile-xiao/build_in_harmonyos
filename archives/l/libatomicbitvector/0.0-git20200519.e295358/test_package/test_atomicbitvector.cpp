// Consumer test for the header-only libatomicbitvector package.
#include <atomic_bitvector.hpp>

#include <cstdio>
#include <thread>
#include <vector>

using atomicbitvector::atomic_bv_t;

static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_checks;                                                            \
        if (!(cond)) {                                                         \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main() {
    atomic_bv_t x(1000);
    CHECK(x.size() == 1000);
    CHECK(x.test(100) == false);
    CHECK(x.set(100) == false);   // returns previous value
    CHECK(x.test(100) == true);
    CHECK(x.set(100) == true);    // already set
    CHECK(x.reset(100) == true);  // returns previous value
    CHECK(x.test(100) == false);
    CHECK(x[7] == false);
    x.set(7, true);
    CHECK(x[7] == true);
    x.set(7, false);
    CHECK(x[7] == false);

    // Iteration visits exactly the set bits, in ascending order.
    atomic_bv_t y(64);
    y.set(3);
    y.set(10);
    y.set(63);
    std::vector<size_t> seen;
    for (auto i : y) seen.push_back(i);
    CHECK(seen.size() == 3);
    CHECK(seen[0] == 3 && seen[1] == 10 && seen[2] == 63);

    // Concurrent disjoint writers: all bits end up set.
    const size_t N = 100000, T = 4;
    atomic_bv_t z(N);
    std::vector<std::thread> threads;
    for (size_t t = 0; t < T; ++t) {
        threads.emplace_back([&z, t, T] {
            for (size_t i = t; i < N; i += T) z.set(i);
        });
    }
    for (auto &th : threads) th.join();
    size_t set_bits = 0;
    for (size_t i = 0; i < N; ++i) {
        if (z.test(i)) ++set_bits;
    }
    CHECK(set_bits == N);

    std::printf("libatomicbitvector consumer test PASS (%d checks)\n", g_checks);
    return 0;
}
