#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <b64.h>

int main(void) {
    const unsigned char *src = (const unsigned char *)"the kinkajou and monkey";
    size_t srclen = strlen((const char *)src);

    char *enc = b64_encode(src, srclen);
    if (!enc) {
        fprintf(stderr, "FAIL: b64_encode returned NULL\n");
        return 1;
    }
    printf("encoded: %s\n", enc);

    size_t decsize = 0;
    unsigned char *dec = b64_decode_ex(enc, strlen(enc), &decsize);
    if (!dec) {
        fprintf(stderr, "FAIL: b64_decode_ex returned NULL\n");
        free(enc);
        return 1;
    }

    int ok = (decsize == srclen) && (memcmp(dec, src, srclen) == 0);
    printf("decoded: %.*s (len=%zu)\n", (int)decsize, (const char *)dec, decsize);
    printf(ok ? "CONSUMER_PASS\n" : "CONSUMER_FAIL\n");

    free(enc);
    free(dec);
    return ok ? 0 : 1;
}
