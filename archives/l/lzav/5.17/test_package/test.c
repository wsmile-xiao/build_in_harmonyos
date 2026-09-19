/*
 * lzav consumer test — verifies a third-party application can use the
 * installed public header-only library through its public API only.
 *
 * Exercises:
 *   1. lzav_compress_bound()          — bound sizing
 *   2. lzav_compress_default()        — compress a realistic buffer
 *   3. lzav_decompress()              — decompress back
 *   4. Round-trip equality + observable result reporting
 */
#include <lzav.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    /* A 1 MiB semi-compressible payload: repeating blocks + noise. */
    const int src_len = 1 << 20;
    unsigned char *src = (unsigned char *)malloc((size_t)src_len);
    unsigned char *comp;
    unsigned char *decomp;
    int comp_len, dec_len, i, ok = 1;

    if (!src) {
        printf("FAIL: malloc(src)\n");
        return 1;
    }
    for (i = 0; i < src_len; i++) {
        src[i] = (unsigned char)('A' + (i % 26));
        if (i % 4096 == 2048)
            src[i] ^= 0x5A; /* sprinkle incompressible-ish bits */
    }

    {
        int bound = lzav_compress_bound(src_len);
        printf("compress_bound(%d) = %d\n", src_len, bound);
        if (bound <= src_len || bound > src_len * 2) {
            printf("FAIL: compress_bound out of plausible range\n");
            ok = 0;
        }
        comp = (unsigned char *)malloc((size_t)bound);
        if (!comp) {
            printf("FAIL: malloc(comp)\n");
            return 1;
        }
        comp_len = lzav_compress_default(src, comp, src_len, bound);
    }

    printf("lzav_compress_default -> comp_len = %d\n", comp_len);
    if (comp_len <= 0 || comp_len >= src_len) {
        printf("FAIL: compression did not produce a smaller buffer\n");
        ok = 0;
    }

    decomp = (unsigned char *)malloc((size_t)src_len);
    if (!decomp) {
        printf("FAIL: malloc(decomp)\n");
        return 1;
    }
    dec_len = lzav_decompress(comp, decomp, comp_len, src_len);
    printf("lzav_decompress -> dec_len = %d\n", dec_len);
    if (dec_len != src_len || memcmp(src, decomp, (size_t)src_len) != 0) {
        printf("FAIL: round-trip mismatch (dec_len=%d, src_len=%d)\n",
               dec_len, src_len);
        ok = 0;
    }

    /* Safety: malformed input must be rejected, not crash (documented OOB). */
    {
        unsigned char junk[64];
        int r;
        memset(junk, 0xFF, sizeof(junk));
        r = lzav_decompress(junk, decomp, (int)sizeof(junk), src_len);
        printf("decompress(malformed) -> %d (expected < 0)\n", r);
        if (r >= 0) {
            printf("FAIL: malformed input not rejected\n");
            ok = 0;
        }
    }

    free(src);
    free(comp);
    free(decomp);

    if (ok) {
        printf("PASS: lzav consumer round-trip verified\n");
        return 0;
    }
    printf("FAIL: lzav consumer test\n");
    return 1;
}