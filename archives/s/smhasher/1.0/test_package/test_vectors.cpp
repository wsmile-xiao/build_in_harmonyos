// test_vectors — MurmurHash3 known vectors, determinism, seed sensitivity,
// and PMurHash32/MurmurHash3_x86_32 agreement (same algorithm upstream:
// both carry verification value 0xB0F57EE3 in src/main.cpp).
#include <cstdio>
#include <cstring>

#include "MurmurHash3.h"
#include "PMurHash.h"

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond) do { \
    g_checks++; \
    if (!(cond)) { \
        printf("FAIL:%d: %s\n", __LINE__, #cond); \
        g_failed++; \
    } \
} while (0)

int main(void) {
    const char *hello = "hello";
    const int hello_len = 5;

    // Known vector (also used by the in-repo MurmurHash3 recipe).
    uint32_t h = 0;
    MurmurHash3_x86_32(hello, hello_len, 0, &h);
    CHECK(h == 0x248bfa47u);

    uint32_t empty = 0xdeadbeefu;
    MurmurHash3_x86_32("", 0, 0, &empty);
    CHECK(empty == 0u);

    uint32_t h_again = 0;
    MurmurHash3_x86_32(hello, hello_len, 0, &h_again);
    CHECK(h == h_again);

    uint32_t h_seed1 = 0;
    MurmurHash3_x86_32(hello, hello_len, 1, &h_seed1);
    CHECK(h_seed1 != h);

    uint64_t o1[2] = {0, 0}, o2[2] = {0, 0}, o3[2] = {0, 0};
    MurmurHash3_x64_128(hello, hello_len, 0, o1);
    MurmurHash3_x64_128(hello, hello_len, 0, o2);
    CHECK(o1[0] == o2[0] && o1[1] == o2[1]);
    MurmurHash3_x64_128(hello, hello_len, 42, o3);
    CHECK(o3[0] != o1[0] || o3[1] != o1[1]);

    uint32_t q1[4] = {0, 0, 0, 0}, q2[4] = {0, 0, 0, 0};
    MurmurHash3_x86_128(hello, hello_len, 0, q1);
    MurmurHash3_x86_128(hello, hello_len, 0, q2);
    CHECK(q1[0] == q2[0] && q1[1] == q2[1] && q1[2] == q2[2] && q1[3] == q2[3]);
    CHECK(q1[0] != 0 || q1[1] != 0 || q1[2] != 0 || q1[3] != 0);

    // PMurHash32 is the portable reimplementation of MurmurHash3_x86_32.
    static const struct {
        const char *key;
        int len;
        uint32_t seed;
    } cases[] = {
        {"hello", 5, 0},
        {"", 0, 0},
        {"", 0, 123},
        {"abc", 3, 42},
        {"hello world", 11, 0xffffffffu},
    };
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        uint32_t a = 0;
        MurmurHash3_x86_32(cases[i].key, cases[i].len, cases[i].seed, &a);
        uint32_t b = PMurHash32(cases[i].seed, cases[i].key, cases[i].len);
        CHECK(a == b);
    }

    printf("test_vectors: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
