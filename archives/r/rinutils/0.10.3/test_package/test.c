/* test_rinutils.c — consumer-side verification (Conan test_package / L1).
 *
 * Verifies that the packaged rinutils headers can be consumed through the
 * installed CMake config (find_package(Rinutils) + Rinutils::Rinutils) and
 * that every header behaves as documented at runtime. Uses CHECK() instead of
 * assert() so that the checks stay active in Release builds (-DNDEBUG).
 *
 * Exit code 0 = all checks passed; non-zero = at least one failure.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <rinutils/rinutils.h>   /* aggregate header (no bit_rw.h) */
#include <rinutils/bit_rw.h>
#include <rinutils/count.h>
#include <rinutils/alloc_wrap.h>
#include <rinutils/exit_error.h>
#include <rinutils/likely.h>
#include <rinutils/longlong.h>
#include <rinutils/min_and_max.h>
#include <rinutils/portable_time.h>
#include <rinutils/str_utils.h>
#include <rinutils/typeof_wrap.h>
#include <rinutils/unused.h>
#include <rinutils/dllexport.h>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond) do {                                                     \
    ++g_checks;                                                              \
    if (cond) { printf("PASS: %s\n", #cond); }                               \
    else { ++g_failures;                                                     \
           printf("FAIL: %s (line %d)\n", #cond, __LINE__); }                \
} while (0)

DLLEXPORT int rinutils_consumer_exported(void)
{
    return 4242;
}

static int takes_unused_param(int x GCC_UNUSED)
{
    return 7;
}

int main(void)
{
    /* rin_cmocka.h itself is exercised by the upstream cmocka test in build(). */
    printf("== rinutils consumer test (13 of 14 installed headers) ==\n");

    /* count.h */
    {
        int myarr[24];
        int mymyarr[7] = {0, 1, 2, 3, 4, 5, 606};
        CHECK(COUNT(myarr) == 24);
        CHECK(LAST(mymyarr) == 606);
    }

    /* min_and_max.h */
    CHECK(max(3, 24) == 24);
    CHECK(min(7, 140) == 7);

    /* str_utils.h */
    {
        const char *s = "Hello";
        CHECK(string_starts_with(s, "Hel", s + 3));
        CHECK(!string_starts_with(s, "Hel", s + 2)); /* wrong length */
        CHECK(!string_starts_with(s, "Hew", s + 3)); /* wrong prefix */
        CHECK(try_str_prefix("PrefixSuffix", "Prefix") != NULL);
        CHECK(strcmp(try_str_prefix("PrefixSuffix", "Prefix"), "Suffix") == 0);
        CHECK(try_str_prefix("PrefixSuffix", "not") == NULL);
    }

    /* alloc_wrap.h */
    {
        size_t n = 4;
        long *buf;
        buf = SMALLOC(buf, n);
        CHECK(buf != NULL);
        if (buf != NULL)
        {
            long *grown;
            buf[3] = 1234;
            grown = SREALLOC(buf, 8);
            CHECK(grown != NULL);
            if (grown != NULL)
            {
                buf = grown;
                CHECK(buf[3] == 1234); /* realloc preserved contents */
                buf[7] = 4321;
                CHECK(buf[7] == 4321);
            }
            free(buf);
        }
    }

    /* bit_rw.h — same expectations as the upstream cmocka test + extras */
    {
        unsigned char buffer[10];
        rin_bit_writer writer;

        rin_bit_writer_init_and_clear(&writer, buffer);
        rin_bit_writer_write(&writer, 4, 5);
        rin_bit_writer_write(&writer, 2, 1);
        CHECK(buffer[0] == (5 | (1 << 4)));
        rin_bit_writer_write(&writer, 4, (2 | (3 << 2)));
        CHECK(buffer[0] == (5 | (1 << 4) | (2 << 6)));
        CHECK(buffer[1] == 3);
        {
            rin_bit_reader reader;
            rin_bit_reader_init(&reader, buffer);
            CHECK(rin_bit_reader_read(&reader, 4) == 5);
            CHECK(rin_bit_reader_read(&reader, 2) == 1);
            CHECK(rin_bit_reader_read(&reader, 4) == (2 | (3 << 2)));
        }
    }
    {
        unsigned char b2[4] = {0xff, 0xff, 0x00, 0x00};
        rin_bit_writer w2;
        rin_bit_reader r2;

        rin_bit_writer_init(&w2, b2);
        rin_bit_writer_overwrite(&w2, 8, 0x5A);
        CHECK(b2[0] == 0x5A);
        rin_bit_writer_overwrite(&w2, 4, 0xA);
        CHECK(b2[1] == 0xFA);
        rin_bit_reader_init(&r2, b2);
        CHECK(rin_bit_reader_read(&r2, 8) == 0x5A);
        CHECK(rin_bit_reader_read(&r2, 4) == 0x0A);
        rin_bit_reader_skip(&r2, 4);
        CHECK(rin_bit_reader_read(&r2, 8) == 0x00);
    }

    /* longlong.h */
    {
        char s[128];
        long long i = 240;
        snprintf(s, sizeof(s), "i = " RIN_LL_FMT, i);
        CHECK(strcmp(s, "i = 240") == 0);
        snprintf(s, sizeof(s), RIN_LL9_FMT, (long long)42);
        CHECK(strcmp(s, "000000042") == 0);
    }

    /* portable_time.h */
    {
        rinutils_portable_time pt = rinutils_get_time();
        CHECK(RIN_TIME_GET_SEC(pt) > 1000000000LL); /* sanity: after 2001 */
        CHECK(RIN_TIME_GET_USEC(pt) >= 0 && RIN_TIME_GET_USEC(pt) < 1000000LL);
    }

    /* likely.h / typeof_wrap.h / unused.h / dllexport.h */
    {
        int v = 1;
        var_AUTO(copy_of_v, v);
        const_AUTO(const_copy_of_v, v);

        CHECK(likely(v == 1));
        CHECK(!likely(v == 2));
        CHECK(unlikely(v == 99) == 0);
        CHECK(copy_of_v == 1);
        CHECK(const_copy_of_v == 1);
        CHECK(rinutils_consumer_exported() == 4242);
        CHECK(takes_unused_param(1) == 7);
    }

    printf("== TOTAL CHECKS: %d, FAILURES: %d ==\n", g_checks, g_failures);
    if (g_failures != 0)
    {
        printf("FAILED: %d of %d checks failed\n", g_failures, g_checks);
        return 1;
    }
    printf("ALL %d CHECKS PASSED\n", g_checks);
    return 0;
}
