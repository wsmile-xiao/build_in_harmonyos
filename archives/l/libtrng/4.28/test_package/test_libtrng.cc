// test_package/test_libtrng.cc — real TRNG API smoke test (consumer-side)
//
// Verifies the libtrng 4.28 package on OHOS aarch64 by:
//   - including official TRNG headers
//   - linking libtrng4
//   - creating a real random-number engine (trng::lcg64)
//   - seeding with a fixed value and asserting determinism
//   - drawing from uniform/uniform_int/normal distributions and checking ranges
//
// Plain C++ with explicit pass/fail accounting (no test framework dependency).
// Returns non-zero on any failure so self.run()/ctest treats it as a failure.

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include <trng/lcg64.hpp>
#include <trng/uniform01_dist.hpp>
#include <trng/uniform_int_dist.hpp>
#include <trng/normal_dist.hpp>

static int g_failures = 0;

#define CHECK(cond)                                                  \
    do {                                                            \
        if (!(cond)) {                                              \
            std::fprintf(stderr, "FAIL [%s:%d] %s\n", __FILE__,     \
                         __LINE__, #cond);                          \
            ++g_failures;                                            \
        }                                                           \
    } while (0)

int main() {
    // 1. Determinism: same seed must yield identical sequences.
    {
        trng::lcg64 r1, r2;
        r1.seed(42ul);
        r2.seed(42ul);
        CHECK(r1 == r2);
        std::vector<trng::lcg64::result_type> a, b;
        a.reserve(64);
        b.reserve(64);
        for (int i = 0; i < 64; ++i) {
            a.push_back(r1());
            b.push_back(r2());
        }
        CHECK(a == b);
    }

    // 2. Raw engine output stays within [min, max].
    {
        trng::lcg64 r;
        r.seed(2026ul);
        const auto lo = trng::lcg64::min();
        const auto hi = trng::lcg64::max();
        bool ok = true;
        for (int i = 0; i < 1000; ++i) {
            const auto v = r();
            if (v < lo || v > hi) { ok = false; break; }
        }
        CHECK(ok);
    }

    // 3. uniform01_dist produces values in [0, 1).
    {
        trng::lcg64 r;
        r.seed(7ul);
        trng::uniform01_dist<double> u;
        bool ok = true;
        for (int i = 0; i < 1000; ++i) {
            const double x = u(r);
            if (!(x >= 0.0 && x < 1.0)) { ok = false; break; }
        }
        CHECK(ok);
    }

    // 4. uniform_int_dist draws within [1, 6].
    {
        trng::lcg64 r;
        r.seed(123ul);
        trng::uniform_int_dist die(1, 6);
        bool ok = true;
        for (int i = 0; i < 10000; ++i) {
            const int face = die(r);
            if (face < 1 || face > 6) { ok = false; break; }
        }
        CHECK(ok);
    }

    // 5. normal_dist draws are finite (not NaN).
    {
        trng::lcg64 r;
        r.seed(99ul);
        trng::normal_dist<double> n(0.0, 1.0);
        bool ok = true;
        for (int i = 0; i < 1000; ++i) {
            const double x = n(r);
            if (std::isnan(x)) { ok = false; break; }
        }
        CHECK(ok);
    }

    // 6. jump2 yields an independent stream from the same seed.
    {
        trng::lcg64 r1, r2;
        r1.seed(5ul);
        r2.seed(5ul);
        r2.jump2(10);
        trng::uniform01_dist<double> u;
        std::vector<double> s1, s2;
        s1.reserve(8);
        s2.reserve(8);
        for (int i = 0; i < 8; ++i) s1.push_back(u(r1));
        for (int i = 0; i < 8; ++i) s2.push_back(u(r2));
        CHECK(s1 != s2);
    }

    if (g_failures == 0) {
        std::printf("test_libtrng: PASS (6 checks)\n");
        return EXIT_SUCCESS;
    }
    std::printf("test_libtrng: FAIL (%d check(s) failed)\n", g_failures);
    return EXIT_FAILURE;
}
