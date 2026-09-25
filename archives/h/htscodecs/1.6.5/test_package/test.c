/* test_package: real consumer-facing verification of the htscodecs public API.
 *
 * Uses only installed public headers (<htscodecs/htscodecs.h>,
 * <htscodecs/rANS_static.h>) and public entry points:
 *   - htscodecs_version()          from htscodecs.h
 *   - rans_compress()/rans_uncompress() from rANS_static.h
 *
 * Performs a real round-trip: compress a DNA-quality buffer, decompress it,
 * and assert byte-for-byte equality.  This is a genuine API call, not a
 * print-only shell (R34/PF3).
 */
#include <htscodecs/htscodecs.h>
#include <htscodecs/rANS_static.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* 64 KiB of quality-like data (values 0..63, representative of
     * sequencing quality scores which this library compresses). */
    const unsigned int N = 65536;
    unsigned char *in  = malloc(N);
    unsigned char *out = NULL;
    unsigned int csize = 0;
    unsigned char *dec = NULL;
    unsigned int usize = 0;
    unsigned int i;
    const char *ver = htscodecs_version();
    int fail = 1;

    if (!in) {
        fprintf(stderr, "FAIL: malloc\n");
        return 1;
    }
    for (i = 0; i < N; i++)
        in[i] = (unsigned char)((i * 7 + (i >> 3)) & 63);

    if (ver == NULL || ver[0] == '\0') {
        fprintf(stderr, "FAIL: htscodecs_version() returned empty\n");
        goto out;
    }

    out = rans_compress(in, N, &csize, 1);
    if (!out || csize == 0 || csize >= N) {
        fprintf(stderr, "FAIL: rans_compress (csize=%u)\n", csize);
        goto out;
    }

    dec = rans_uncompress(out, csize, &usize);
    if (!dec || usize != N) {
        fprintf(stderr, "FAIL: rans_uncompress (usize=%u want=%u)\n", usize, N);
        goto out;
    }

    if (memcmp(in, dec, N) != 0) {
        fprintf(stderr, "FAIL: round-trip mismatch\n");
        goto out;
    }

    printf("PASS: htscodecs %s rANS round-trip %u -> %u bytes\n",
           ver, N, csize);
    fail = 0;
out:
    free(in);
    free(out);
    free(dec);
    return fail;
}
