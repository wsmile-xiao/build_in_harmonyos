/* test_fribidi.c — Conan L1 test for fribidi 1.0.17
 * Verifies: version info (incl. 1.0.17 string), UTF-8 charset conversion,
 * bidi algorithm (log2vis), mirror char lookup (1.0.17 mirroring fixes).
 */
#include <fribidi/fribidi.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int errors = 0;

    /* 1. Verify version string is accessible and is 1.0.17 */
    const char *ver = fribidi_version_info;
    if (ver == NULL || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: fribidi_version_info is empty\n");
        errors++;
    } else if (strstr(ver, "1.0.17") == NULL) {
        fprintf(stderr, "FAIL: fribidi_version_info does not contain 1.0.17: %.40s\n", ver);
        errors++;
    } else {
        printf("OK: fribidi version = 1.0.17 (info string accessible)\n");
    }

    /* 2. Convert UTF-8 to Unicode and back */
    const char *utf8_input = "Hello";
    FriBidiChar unicode_buf[256];
    FriBidiStrIndex ulen = fribidi_charset_to_unicode(
        FRIBIDI_CHAR_SET_UTF8, utf8_input, strlen(utf8_input), unicode_buf);
    if (ulen != 5) {
        fprintf(stderr, "FAIL: charset_to_unicode returned %ld, expected 5\n", (long)ulen);
        errors++;
    } else {
        printf("OK: UTF-8 to Unicode conversion, len=%ld\n", (long)ulen);
    }

    /* 3. Run bidi algorithm (log2vis) on an RTL string */
    FriBidiChar logical[] = {0x0628, 0x0627, 0x062A};  /* Arabic: baa, alef, taa */
    FriBidiChar visual[3];
    FriBidiLevel levels[3];
    FriBidiParType base_dir = FRIBIDI_PAR_RTL;
    fribidi_boolean success = fribidi_log2vis(
        logical, 3, &base_dir, visual, NULL, NULL, levels);
    if (!success) {
        fprintf(stderr, "FAIL: fribidi_log2vis returned 0\n");
        errors++;
    } else {
        printf("OK: log2vis base level = %d\n", (int)base_dir);
    }

    /* 4. Mirror char lookup (1.0.17: N0/mirroring fixes per NEWS) */
    FriBidiChar mirrored = 0;
    fribidi_boolean mok = fribidi_get_mirror_char(0x0028 /* '(' */, &mirrored);
    if (!mok || mirrored != 0x0029 /* ')' */) {
        fprintf(stderr, "FAIL: get_mirror_char returned %d, mirrored=U+%04X\n", (int)mok, (unsigned)mirrored);
        errors++;
    } else {
        printf("OK: mirror char U+0028 -> U+%04X\n", (unsigned)mirrored);
    }

    if (errors > 0) {
        fprintf(stderr, "FAILED with %d errors\n", errors);
        return 1;
    }
    printf("All tests passed\n");
    return 0;
}
