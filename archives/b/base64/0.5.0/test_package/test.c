#include <libbase64.h>
#include <stdio.h>
#include <string.h>

/* Consumer test: exercise the public base64_encode/base64_decode API
 * through the installed public header and linked library only. */

static int check(const char *plain) {
    size_t srclen = strlen(plain);
    char enc[256], dec[256];
    size_t enclen = 0, declen = 0;
    int rc = 0;

    base64_encode(plain, srclen, enc, &enclen, 0);
    /* Empty input legitimately encodes to zero bytes. */
    if (srclen > 0 && enclen == 0) {
        fprintf(stderr, "FAIL: encode produced no output\n");
        return 1;
    }
    rc = base64_decode(enc, enclen, dec, &declen, 0);
    if (rc != 1 || declen != srclen || memcmp(dec, plain, srclen) != 0) {
        fprintf(stderr, "FAIL: roundtrip mismatch for '%s'\n", plain);
        return 1;
    }
    printf("roundtrip ok: '%s' -> %zu bytes encoded -> %zu bytes decoded\n",
           plain, enclen, declen);
    return 0;
}

int main(void) {
    int fails = 0;
    fails += check("");
    fails += check("Hello, OpenHarmony!");
    fails += check("The quick brown fox jumps over the lazy dog.");
    if (fails != 0) {
        fprintf(stderr, "test_base64: %d check(s) failed\n", fails);
        return 1;
    }
    printf("test_base64: all consumer checks passed\n");
    return 0;
}
