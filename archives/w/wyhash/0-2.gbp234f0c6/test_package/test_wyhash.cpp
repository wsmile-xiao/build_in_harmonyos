// Consumer test for the header-only wyhash package.
// Includes <wyhash.h> through the installed CMake target and verifies the
// official upstream vectors plus the public utility API (R34).
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <wyhash.h>

namespace {

int g_checks = 0;

void fail(const char *what, std::uint64_t got, std::uint64_t expected) {
    std::fprintf(stderr, "FAIL %s: got 0x%016llx expected 0x%016llx\n",
                 what, static_cast<unsigned long long>(got),
                 static_cast<unsigned long long>(expected));
    std::exit(1);
}

void check_hash(const char *text, std::uint64_t seed, std::uint64_t expected) {
    std::uint64_t got = wyhash(text, std::strlen(text), seed, _wyp);
    ++g_checks;
    if (got != expected) {
        fail(text, got, expected);
    }
}

void check_u64(const char *what, std::uint64_t got, std::uint64_t expected) {
    ++g_checks;
    if (got != expected) {
        fail(what, got, expected);
    }
}

}  // namespace

int main() {
    // Upstream test_vector.cpp vectors, pinned at commit 234f0c6.
    check_hash("", 0, 0x42bc986dc5eec4d3ULL);
    check_hash("a", 1, 0x84508dc903c31551ULL);
    check_hash("abc", 2, 0x0bc54887cfc9ecb1ULL);
    check_hash("message digest", 3, 0xadc146444841c430ULL);
    check_hash("abcdefghijklmnopqrstuvwxyz", 4, 0x4c0977bd4f14f34aULL);
    check_hash("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", 5,
               0x6f8bd609a8a276d2ULL);
    check_hash("1234567890123456789012345678901234567890123456789012345678901234567890"
               "1234567890", 6, 0x498d7c21668259adULL);

    check_u64("wyhash64(0,0)", wyhash64(0, 0), 0x60c06e5aa6716029ULL);
    check_u64("wyhash64(1,2)", wyhash64(1, 2), 0x12f633807d6dd48cULL);
    check_u64("wyhash64(deadbeef,12345678)",
              wyhash64(0xdeadbeefULL, 0x12345678ULL), 0x3d3427e882f3d554ULL);
    check_u64("wyhash64(~0,~0)", wyhash64(~0ULL, ~0ULL), 0x8de38748e71c42a8ULL);

    std::uint64_t seed = 0;
    check_u64("wyrand#0", wyrand(&seed), 0x111cb3a78f59a58eULL);
    check_u64("wyrand#1", wyrand(&seed), 0xceabd938ff4e856dULL);
    check_u64("wyrand#2", wyrand(&seed), 0x61fb51318f47d2a4ULL);
    check_u64("wyrand seed advance", seed, 0xe162582d6a382c8dULL);
    check_u64("wyrand#3", wyrand(&seed), 0x78bd03c491909760ULL);

    check_u64("wy2u0k", wy2u0k(0x123456789abcdef0ULL, 5), 0x0ULL);
    check_u64("wy2u0k(~0,3)", wy2u0k(~0ULL, 3), 0x2ULL);

    // Exercise the >64-byte accumulation path.
    unsigned char buffer[300];
    for (int i = 0; i < 200; ++i) {
        buffer[i] = static_cast<unsigned char>(i & 0xff);
    }
    check_u64("wyhash big200", wyhash(buffer, 200, 0xabcdef01ULL, _wyp),
              0xd3444225426e06beULL);
    std::memset(buffer, 0, sizeof(buffer));
    check_u64("wyhash zeros300", wyhash(buffer, 300, 7, _wyp), 0xdb890c4a932fdefeULL);

    std::uint64_t r = wyhash64(1, 2);
    double uniform = wy2u01(r);
    ++g_checks;
    if (!(uniform >= 0.0 && uniform < 1.0)) {
        std::fprintf(stderr, "FAIL wy2u01 out of range: %f\n", uniform);
        std::exit(1);
    }
    double gaussian = wy2gau(r);
    ++g_checks;
    if (!(gaussian >= -3.0 && gaussian < 3.0)) {
        std::fprintf(stderr, "FAIL wy2gau out of range: %f\n", gaussian);
        std::exit(1);
    }

    std::printf("wyhash consumer test PASS (%d checks)\n", g_checks);
    return 0;
}
