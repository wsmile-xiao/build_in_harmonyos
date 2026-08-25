// test_package/test.cpp — libdivide 5.3.0 consumer test
//
// Exercises the most basic, portable scalar API of libdivide:
// constructs dividers and performs optimized integer division, then
// verifies the results match plain division. No SSE/AVX/AVX512 paths.

#include <libdivide.h>

#include <cstdio>
#include <cstdint>

static int test_u32() {
    // unsigned 32-bit divider
    libdivide::divider<uint32_t> d(7);
    for (uint32_t n = 0; n <= 1000; ++n) {
        if (d.divide(n) != (n / 7u)) {
            std::printf("FAIL u32: n=%u got=%u exp=%u\n", n, d.divide(n), n / 7u);
            return 1;
        }
    }
    return 0;
}

static int test_s64() {
    // signed 64-bit divider (covers negative results)
    libdivide::divider<int64_t> d(1000003LL);
    int64_t cases[] = {
        0LL, 1LL, 7LL, 100LL, 999999LL, 1000003LL,
        1000004LL, 1000003000LL, -1000003000LL, -7LL, -1LL
    };
    for (int64_t n : cases) {
        if (d.divide(n) != (n / 1000003LL)) {
            std::printf("FAIL s64: n=%lld got=%lld exp=%lld\n",
                        (long long)n, (long long)d.divide(n),
                        (long long)(n / 1000003LL));
            return 1;
        }
    }
    return 0;
}

static int test_branchfree() {
    // branchfree divider (unsigned 32-bit, divisor != 1)
    libdivide::branchfree_divider<uint32_t> bd(3);
    for (uint32_t n = 0; n <= 900; ++n) {
        if (bd.divide(n) != (n / 3u)) {
            std::printf("FAIL bf: n=%u got=%u exp=%u\n", n, bd.divide(n), n / 3u);
            return 1;
        }
    }
    return 0;
}

static int test_operator_overload() {
    // operator/ overload: n / divider
    libdivide::divider<int32_t> d(13);
    for (int32_t n = -200; n <= 200; ++n) {
        if ((n / d) != (n / 13)) {
            std::printf("FAIL op/: n=%d got=%d exp=%d\n", n, n / d, n / 13);
            return 1;
        }
    }
    return 0;
}

static int test_recover() {
    // recover() returns the original divisor
    libdivide::divider<int64_t> d(999983LL);
    if (d.recover() != 999983LL) {
        std::printf("FAIL recover: got=%lld\n", (long long)d.recover());
        return 1;
    }
    return 0;
}

static int test_version() {
    // Sanity: the header advertises 5.3.0
    if (LIBDIVIDE_VERSION_MAJOR != 5 ||
        LIBDIVIDE_VERSION_MINOR != 3 ||
        LIBDIVIDE_VERSION_PATCH != 0) {
        std::printf("FAIL version: %d.%d.%d\n",
                    LIBDIVIDE_VERSION_MAJOR,
                    LIBDIVIDE_VERSION_MINOR,
                    LIBDIVIDE_VERSION_PATCH);
        return 1;
    }
    return 0;
}

int main() {
    int rc = 0;
    rc |= test_u32();
    rc |= test_s64();
    rc |= test_branchfree();
    rc |= test_operator_overload();
    rc |= test_recover();
    rc |= test_version();

    if (rc != 0) {
        std::printf("test libdivide 5.3.0: FAILED\n");
        return 1;
    }

    std::printf("test libdivide 5.3.0: OK\n");
    return 0;
}
