/*
 * Consumer test for the installed pcg-cpp package.
 *
 * Calls the public API of the library and asserts real behaviour.
 * The golden sequences below are the values actually produced by the
 * upstream test suite (test-high/) on this adaptation, as recorded in
 * test-high/actual/check-pcg32.out and check-pcg64.out.
 */
#include <cstdint>
#include <cstdio>
#include <random>

#include "pcg_random.hpp"
#include "pcg_extras.hpp"

static int failures = 0;

static void check(bool cond, const char* what)
{
    if(cond)
        printf("PASS: %s\n", what);
    else
    {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

int main(void)
{
    /* 1. pcg32 seeded with (42u, 54u) reproduces the upstream golden
     *    sequence (test-high/actual/check-pcg32.out, Round 1). */
    {
        pcg32 rng(42u, 54u);
        const uint32_t expect[6] = {
            0xa15c02b7u, 0x7b47f409u, 0xba1d3330u,
            0x83d2f293u, 0xbfa4784bu, 0xcbed606eu,
        };
        bool ok = true;
        for(int i = 0; i < 6; ++i)
            ok = ok && (rng() == expect[i]);
        check(ok, "pcg32(42,54) matches upstream golden sequence");
    }

    /* 2. pcg64 seeded with (42u, 54u) — upstream check-pcg64 defines
     *    TWO_ARG_INIT — reproduces the golden sequence
     *    (test-high/actual/check-pcg64.out, Round 1). */
    {
        pcg64 rng(42u, 54u);
        const uint64_t expect[6] = {
            0x86b1da1d72062b68ull, 0x1304aa46c9853d39ull,
            0xa3670e9e0dd50358ull, 0xf9090e529a7dae00ull,
            0xc85b9fd837996f2cull, 0x606121f8e3919196ull,
        };
        bool ok = true;
        for(int i = 0; i < 6; ++i)
            ok = ok && (rng() == expect[i]);
        check(ok, "pcg64(42,54) matches upstream golden sequence");
    }

    /* 3. backstep() rewinds the stream so replay yields the same values. */
    {
        pcg32 rng(42u, 54u);
        uint32_t first[3];
        uint32_t again[3];
        for(auto& v : first)
            v = rng();
        rng.backstep(3);
        bool ok = true;
        for(auto& v : again)
            v = rng();
        for(int i = 0; i < 3; ++i)
            ok = ok && (first[i] == again[i]);
        check(ok, "pcg32 backstep(3) replays the same values");
    }

    /* 4. pcg_extras::seed_seq_from<std::random_device> reseeds the engine
     *    and generation keeps working (API smoke through real use). */
    {
        pcg32 rng(42u, 54u);
        const uint32_t before = rng();
        pcg_extras::seed_seq_from<std::random_device> seed_seq;
        rng.seed(seed_seq);
        const uint32_t after = rng();
        check(before != after, "reseed via pcg_extras changes the stream");
    }

    if(failures != 0)
    {
        printf("%d check(s) FAILED\n", failures);
        return 1;
    }
    printf("all pcg-cpp consumer checks passed\n");
    return 0;
}
