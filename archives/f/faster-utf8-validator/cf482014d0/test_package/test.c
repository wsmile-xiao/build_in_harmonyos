/* test_package consumer test — calls the public API z_validate_utf8()
 * with meaningful inputs and asserts observable results (R34: no empty shell). */
#include <stdio.h>
#include <string.h>
#include <z_validate.h>

static int expect_valid(const char *label, const char *s, int want) {
    int got = z_validate_utf8(s, strlen(s));
    if (got != want) {
        printf("FAIL %s: want=%d got=%d\n", label, want, got);
        return 1;
    }
    printf("PASS %s: %d (as expected)\n", label, got);
    return 0;
}

int main(void) {
    int fails = 0;
    /* valid UTF-8: ASCII, 2-byte, 3-byte CJK, 4-byte emoji */
    fails += expect_valid("ascii", "hello", 1);
    fails += expect_valid("latin-1", "caf\xC3\xA9", 1);
    fails += expect_valid("cjk", "\xE4\xB8\xAD\xE6\x96\x87", 1);
    fails += expect_valid("emoji", "\xF0\x9F\x98\x80", 1);
    fails += expect_valid("mixed", "a\xC2\xA2\xE2\x82\xAC\xF0\x9F\x98\x80", 1);
    /* invalid: overlong, surrogate, >U+10FFFF, truncated, stray continuation */
    fails += expect_valid("overlong-C0", "\xC0\x80", 0);
    fails += expect_valid("overlong-E0", "\xE0\x80\x80", 0);
    fails += expect_valid("surrogate", "\xED\xA0\x80", 0);
    fails += expect_valid("too-high", "\xF4\x90\x80\x80", 0);
    fails += expect_valid("truncated", "\xE4\xB8", 0);
    fails += expect_valid("stray-cont", "\x80", 0);
    if (fails == 0)
        printf("test_package: all %d assertions passed\n", 12);
    else
        printf("test_package: %d assertions failed\n", fails);
    return fails ? 1 : 0;
}
