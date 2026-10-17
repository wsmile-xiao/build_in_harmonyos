#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <libnu/libnu.h>

static int checks = 0;
static int passed = 0;
#define CHECK(cond, name) do { \
    checks++; \
    if (cond) { passed++; printf("CASE PASS: %s\n", name); } \
    else { printf("CASE FAIL: %s\n", name); } \
} while (0)

int main(void) {
    /* 1: UTF-8 decode U+00E9 */
    {
        const char *s = "\xc3\xa9";
        uint32_t u = 0;
        const char *p = nu_utf8_read(s, &u);
        CHECK(p != 0 && u == 0xE9, "utf8-decode-e9");
    }
    /* 2: UTF-8 encode U+4E2D round-trip */
    {
        char buf[16] = {0};
        char *p = nu_utf8_write(0x4E2D, buf);
        uint32_t u = 0;
        const char *q = nu_utf8_read(buf, &u);
        CHECK(p != 0 && q != 0 && u == 0x4E2D, "utf8-roundtrip-zhong");
    }
    /* 3: UTF-16LE round-trip U+1F600 */
    {
        char w[8] = {0};
        char *pw = nu_utf16le_write(0x1F600, w);
        uint32_t u = 0;
        const char *q = nu_utf16le_read(w, &u);
        CHECK(pw != 0 && q != 0 && u == 0x1F600, "utf16le-roundtrip-emoji");
    }
    /* 4: validation rejects overlong sequence */
    {
        const char *bad = "\xc0\xaf";
        const char *v = nu_validate(bad, 2, nu_utf8_validread);
        CHECK(v != 0, "validate-rejects-overlong");
    }
    /* 5: version string non-empty */
    {
        const char *ver = nu_version();
        CHECK(ver != 0 && strlen(ver) > 0, "version-non-empty");
    }
    printf("SUMMARY: %d/%d passed\n", passed, checks);
    return (passed == checks) ? 0 : 1;
}
