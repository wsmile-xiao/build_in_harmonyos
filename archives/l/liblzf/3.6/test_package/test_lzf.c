/* test_lzf.c — consumer verification for liblzf 3.6 (ctest case driver).
 *
 * Usage: test_lzf <case>
 * Each case exercises the real liblzf API and prints one deterministic
 * result line with measured numbers:
 *   LZF-CASE <name>: PASS <details with real sizes>
 *   LZF-CASE <name>: FAIL <reason>
 * Exit code is 0 only when the case passes, so ctest Passed/Failed comes
 * straight from real assertions (a stub binary can never fake the sizes).
 *
 * Cases:
 *   roundtrip_text    compress ~45KB repetitive text, must shrink, round-trip equal
 *   roundtrip_binary  compress 32KB fixed-seed xorshift bytes, round-trip equal
 *                     (cs == 0 is the valid "incompressible" signal, accepted)
 *   roundtrip_large   compress 256KB zeros, ratio must be < 5%, round-trip equal
 *   corrupt_einval    hand-crafted invalid backref {0x20,0x00} must fail EINVAL
 *   small_out_e2big   hand-crafted 32-byte literal run into 4-byte buffer must fail E2BIG
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lzf.h>

static int fail(const char *name, const char *why)
{
    printf("LZF-CASE %s: FAIL %s\n", name, why);
    fflush(stdout);
    return 1;
}

static int pass(const char *name, const char *detail)
{
    printf("LZF-CASE %s: PASS %s\n", name, detail);
    fflush(stdout);
    return 0;
}

/* Deterministic PRNG (xorshift32, fixed seed) for the binary case. */
static unsigned int rng_state = 0x12345678u;
static unsigned char rng_next(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 17;
    rng_state ^= rng_state << 5;
    return (unsigned char)(rng_state & 0xffu);
}

static int check_roundtrip(const char *name, const unsigned char *in, unsigned int in_len,
                           int must_shrink_num, int must_shrink_den)
{
    /* Worst case per lzf.h: output may exceed input by < 4%. */
    unsigned int out_cap = in_len + in_len / 16 + 64;
    unsigned char *comp = (unsigned char *)malloc(out_cap);
    unsigned char *back = (unsigned char *)malloc(in_len ? in_len : 1);
    unsigned int cs, ds;
    char detail[160];
    int rc;

    if (!comp || !back) {
        free(comp);
        free(back);
        return fail(name, "malloc failed");
    }
    errno = 0;
    cs = lzf_compress(in, in_len, comp, out_cap);
    if (cs == 0) {
        /* Valid "not compressible" signal only when shrinking is optional. */
        if (must_shrink_num == 0) {
            snprintf(detail, sizeof(detail), "in_len=%u reported incompressible (cs=0)", in_len);
            free(comp);
            free(back);
            return pass(name, detail);
        }
        free(comp);
        free(back);
        return fail(name, "lzf_compress returned 0 for compressible input");
    }
    if (must_shrink_num != 0 && (unsigned long long)cs * must_shrink_den >= (unsigned long long)in_len * must_shrink_num) {
        snprintf(detail, sizeof(detail), "in_len=%u cs=%u, no real compression", in_len, cs);
        free(comp);
        free(back);
        return fail(name, detail);
    }
    errno = 0;
    ds = lzf_decompress(comp, cs, back, in_len);
    if (ds != in_len) {
        snprintf(detail, sizeof(detail), "decompressed %u bytes, expected %u (errno=%d)", ds, in_len, errno);
        free(comp);
        free(back);
        return fail(name, detail);
    }
    rc = memcmp(in, back, in_len) != 0;
    snprintf(detail, sizeof(detail), "in_len=%u cs=%u ds=%u byte-equal", in_len, cs, ds);
    free(comp);
    free(back);
    return rc ? fail(name, detail) : pass(name, detail);
}

static int case_roundtrip_text(void)
{
    static const char *sentence =
        "liblzf is an extremely fast data compression library. ";
    unsigned int unit = (unsigned int)strlen(sentence);
    unsigned int in_len = unit * 800u; /* ~45KB */
    unsigned char *in = (unsigned char *)malloc(in_len);
    unsigned int i;
    int rc;

    if (!in)
        return fail("roundtrip_text", "malloc failed");
    for (i = 0; i < 800u; i++)
        memcpy(in + i * unit, sentence, unit);
    /* Highly repetitive: demand real compression (cs < in_len / 2). */
    rc = check_roundtrip("roundtrip_text", in, in_len, 1, 2);
    free(in);
    return rc;
}

static int case_roundtrip_binary(void)
{
    unsigned int in_len = 32768u;
    unsigned char *in = (unsigned char *)malloc(in_len);
    unsigned int i;
    int rc;

    if (!in)
        return fail("roundtrip_binary", "malloc failed");
    for (i = 0; i < in_len; i++)
        in[i] = rng_next();
    /* PRNG output: shrinking optional (must_shrink 0/1 accepts cs == 0). */
    rc = check_roundtrip("roundtrip_binary", in, in_len, 0, 1);
    free(in);
    return rc;
}

static int case_roundtrip_large(void)
{
    unsigned int in_len = 262144u; /* 256KB zeros */
    unsigned char *in = (unsigned char *)calloc(1, in_len);
    int rc;

    if (!in)
        return fail("roundtrip_large", "calloc failed");
    /* Zeros compress massively: demand ratio < 5%. */
    rc = check_roundtrip("roundtrip_large", in, in_len, 1, 20);
    free(in);
    return rc;
}

static int case_corrupt_einval(void)
{
    /* ctrl 0x20 = backref, len 1, offset high 0; next byte 0x00 keeps the
     * offset at 1 while zero bytes have been produced -> ref < out_data,
     * lzf_d.c must return 0 with errno == EINVAL. Reads exactly 2 bytes. */
    static const unsigned char bad[] = { 0x20, 0x00 };
    unsigned char out[64];
    unsigned int rc;

    memset(out, 0xaa, sizeof(out));
    errno = 0;
    rc = lzf_decompress(bad, sizeof(bad), out, sizeof(out));
    if (rc != 0)
        return fail("corrupt_einval", "corrupt stream unexpectedly decoded");
    if (errno != EINVAL) {
        char detail[64];
        snprintf(detail, sizeof(detail), "errno=%d, expected EINVAL(%d)", errno, EINVAL);
        return fail("corrupt_einval", detail);
    }
    return pass("corrupt_einval", "rc=0 errno=EINVAL as documented in lzf.h");
}

static int case_small_out_e2big(void)
{
    /* ctrl 0x1f = literal run of 32 bytes; a 4-byte output buffer is too
     * small -> lzf_d.c must return 0 with errno == E2BIG. */
    static const unsigned char lit[33] = {
        0x1f,
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f',
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'
    };
    unsigned char out[4];
    unsigned int rc;

    errno = 0;
    rc = lzf_decompress(lit, sizeof(lit), out, sizeof(out));
    if (rc != 0)
        return fail("small_out_e2big", "oversized literal unexpectedly decoded");
    if (errno != E2BIG) {
        char detail[64];
        snprintf(detail, sizeof(detail), "errno=%d, expected E2BIG(%d)", errno, E2BIG);
        return fail("small_out_e2big", detail);
    }
    return pass("small_out_e2big", "rc=0 errno=E2BIG as documented in lzf.h");
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: test_lzf <roundtrip_text|roundtrip_binary|roundtrip_large|corrupt_einval|small_out_e2big>\n");
        return 2;
    }
    if (strcmp(argv[1], "roundtrip_text") == 0)
        return case_roundtrip_text();
    if (strcmp(argv[1], "roundtrip_binary") == 0)
        return case_roundtrip_binary();
    if (strcmp(argv[1], "roundtrip_large") == 0)
        return case_roundtrip_large();
    if (strcmp(argv[1], "corrupt_einval") == 0)
        return case_corrupt_einval();
    if (strcmp(argv[1], "small_out_e2big") == 0)
        return case_small_out_e2big();
    fprintf(stderr, "test_lzf: unknown case '%s'\n", argv[1]);
    return 2;
}
