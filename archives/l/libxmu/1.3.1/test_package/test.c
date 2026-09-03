/*
 * libxmu 1.3.1 Conan test_package — L1 official test (R34: substantive API call)
 *
 * Calls XmuCompareISOLatin1() from libXmuu (the Xt-independent subset of libXmu).
 * This is the same API exercised by the upstream "Lower" unit test, ensuring the
 * test_package verifies a real, exported symbol of the packaged library.
 */
#include <X11/Xmu/CharSet.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *a = "Hello";
    const char *b = "hello";

    int cmp = XmuCompareISOLatin1(a, b);
    /* 'H' (0x48) vs 'h' (0x68): ISO-Latin-1 comparison is case-insensitive,
       XmuCompareISOLatin1 returns 0 for equal-after-folding. */
    if (cmp != 0) {
        fprintf(stderr, "FAIL: XmuCompareISOLatin1(\"%s\", \"%s\") = %d, expected 0\n",
                a, b, cmp);
        return 1;
    }

    int diff = XmuCompareISOLatin1("abc", "abd");
    if (diff >= 0) {
        fprintf(stderr, "FAIL: XmuCompareISOLatin1(\"abc\", \"abd\") = %d, expected < 0\n",
                diff);
        return 1;
    }

    printf("PASS: libXmuu XmuCompareISOLatin1 API works (cmp=%d, diff=%d)\n", cmp, diff);
    return 0;
}
