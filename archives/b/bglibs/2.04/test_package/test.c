/* Consumer test for bglibs 2.04 on OHOS (aarch64).
 *
 * Exercises three public modules as a library consumer would: str
 * (dynamic strings), fmt (number formatting) and crc32 (table-driven
 * CRC-32).  Every check asserts real behaviour; the exit code reflects
 * the number of failed checks.
 */
#include <bglibs/str.h>
#include <bglibs/fmt.h>
#include <bglibs/crc32.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        ++failures; \
    } \
} while (0)

int main(void)
{
    /* --- str module: init, append, formatted append, prefix, free --- */
    str s;
    CHECK(str_init(&s) == 1);
    CHECK(str_copys(&s, "hello") == 1);
    CHECK(s.len == 5);
    CHECK(strcmp(s.s, "hello") == 0);
    CHECK(str_cats(&s, " world") == 1);
    CHECK(strcmp(s.s, "hello world") == 0);
    /* Append " 42" via fmt_ulldec + str_cats: bglibs formatting functions
     * have no printf semantics (str_catf uses the bglibs format language),
     * so we compose the number explicitly. */
    {
        char numbuf[16];
        unsigned m = fmt_ulldec(numbuf, 42ULL);
        numbuf[m] = '\0';
        CHECK(m == 2);
        CHECK(str_catc(&s, ' ') == 1);
        CHECK(str_cats(&s, numbuf) == 1);
    }
    CHECK(strcmp(s.s, "hello world 42") == 0);
    CHECK(s.len == strlen("hello world 42"));
    CHECK(str_starts(&s, "hello") == 1);
    CHECK(str_starts(&s, "world") == 0);
    str_free(&s);
    CHECK(s.s == 0 && s.len == 0 && s.size == 0);

    /* --- fmt module: unsigned long long decimal formatting --- */
    char buf[32];
    unsigned n = fmt_ulldec(buf, 1234567890ULL);
    buf[n] = '\0';
    CHECK(n == 10);
    CHECK(strcmp(buf, "1234567890") == 0);

    /* --- crc32 module: IEEE CRC-32 over the standard check vector --- */
    const char* vector = "123456789";
    uint32 c = crc32_block(vector, 9);
    CHECK(c == 0xCBF43926UL);

    if (failures) {
        fprintf(stderr, "bglibs consumer test: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("bglibs consumer test: all checks passed\n");
    return 0;
}
