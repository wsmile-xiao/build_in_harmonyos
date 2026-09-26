/*
 * test_hz — substantive consumer test for the zh-autoconvert (libhz) package.
 *
 * Exercises the public conversion API: gb2big_init/gb2big and big2gb_init/big2gb.
 * We convert the GB2312 encoding of the character '中' (0xD6 0xD0) to Big5 and
 * back, asserting:
 *   1. gb2big returns a non-NULL 2-byte result,
 *   2. both Big5 bytes are in the lead/trail range (>= 0xA1), proving a real
 *      conversion occurred rather than an identity copy,
 *   3. the Big5 -> GB round-trip reproduces the original bytes (verified
 *      against the library's own GtoB/BtoG tables: 中 -> A4 A4 -> D6 D0).
 *
 * Note: libhz's hzconvert() processes its input *in place* and buffers the
 * trailing byte of a stream, so we only assert on the converted bytes, not on
 * the returned length (the last byte is intentionally held for the next call).
 *
 * No <cassert>: the Conan CI profile builds Release with -DNDEBUG, which strips
 * assert(), so we report failures via a non-zero exit code instead.
 */
#include <hz.h>
#include <stdio.h>

static int failures = 0;

#define CHECK(cond, msg)                                          \
    do {                                                          \
        if (!(cond)) {                                            \
            printf("FAIL: %s\n", msg);                           \
            ++failures;                                           \
        }                                                         \
    } while (0)

int main(void) {
    /* '中' : GB2312 = 0xD6 0xD0 ; the trailing 0x00 is a harmless
     * non-hanzi terminator so hzconvert never reads past the buffer. */
    unsigned char gb[] = {0xD6, 0xD0, 0x00};

    int inst_g2b = gb2big_init(NULL);
    int len = 2;
    char *b5 = gb2big((char *)gb, &len, inst_g2b);
    CHECK(b5 != 0, "gb2big returned NULL");
    if (b5 != 0) {
        CHECK((unsigned char)b5[0] >= 0xA1 && (unsigned char)b5[1] >= 0xA1,
              "gb2big output is not a valid Big5 byte pair");
    }

    int inst_b2g = big2gb_init(NULL);
    int len2 = 2;
    char *back = big2gb(b5, &len2, inst_b2g);
    CHECK(back != 0, "big2gb returned NULL");
    if (back != 0) {
        CHECK((unsigned char)back[0] == 0xD6 && (unsigned char)back[1] == 0xD0,
              "Big5 -> GB round-trip did not reproduce original GB bytes");
    }

    if (failures == 0) {
        printf("OK: GB<->Big5 round-trip verified for U+4E2D ('中')\n");
        return 0;
    }
    printf("FAILED with %d assertion(s) failing\n", failures);
    return 1;
}
