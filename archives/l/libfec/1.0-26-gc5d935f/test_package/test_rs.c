/* test_rs.c — Reed-Solomon consumer test for the packaged libfec.
 *
 * Exercises the general-purpose GF(256) RS(255,223) codec through the
 * public char and int APIs: encode, clean decode, correction of random
 * symbol errors up to the t=16 limit, the 2t erasure channel, and the
 * uncorrectable (> t errors) path. The error patterns come from a fixed
 * LCG so every run is deterministic.
 */
#include <stdio.h>
#include <string.h>

#include "fec.h"

#define NROOTS 32
#define N 255
#define K (N - NROOTS) /* 223 */

static unsigned long lcg_state = 0x5eed1234UL;
static unsigned int lcg(void)
{
    lcg_state = lcg_state * 1103515245UL + 12345UL;
    return (unsigned int)((lcg_state >> 16) & 0x7fff);
}

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        checks++;                                                           \
        if (!(cond)) {                                                      \
            failures++;                                                     \
            printf("FAIL %s:%d %s\n", __FILE__, __LINE__, msg);             \
        }                                                                   \
    } while (0)

static unsigned char block[N];
static unsigned char reference[N];
static unsigned int iblock[N];
static unsigned int ireference[N];
static int corrupted[N];

/* Corrupt exactly n distinct positions of block[] */
static void corrupt(unsigned char blk[N], int n)
{
    int i, j, pos;
    for (i = 0; i < n; i++) {
        do {
            pos = (int)(lcg() % N);
            for (j = 0; j < i; j++) {
                if (corrupted[j] == pos) break;
            }
        } while (j < i);
        corrupted[i] = pos;
        blk[pos] ^= (unsigned char)(1u + lcg() % 255u);
    }
}

int main(void)
{
    int i, dcount;

    /* ── char codec: RS(255,223), gf 0x11d, fcr=1, prim=1 ── */
    void *rs = init_rs_char(8, 0x11d, 1, 1, NROOTS, 0);
    CHECK(rs != NULL, "init_rs_char");

    for (i = 0; i < K; i++) {
        reference[i] = block[i] = (unsigned char)lcg();
    }

    /* 1. Encode and verify the parity tail differs from garbage */
    memset(block + K, 0xAA, NROOTS);
    encode_rs_char(rs, block, block + K);
    checks++;
    if (memcmp(block + K, reference + K, NROOTS) == 0) {
        failures++;
        printf("FAIL parity tail left untouched by encoder\n");
    }
    memcpy(reference + K, block + K, NROOTS);

    /* 2. Clean codeword decodes to zero corrections */
    dcount = decode_rs_char(rs, block, NULL, 0);
    CHECK(dcount == 0, "clean decode returns 0");
    CHECK(memcmp(block, reference, N) == 0, "clean decode leaves block intact");

    /* 3. t = 16 random errors are corrected in place */
    corrupt(block, 16);
    dcount = decode_rs_char(rs, block, NULL, 0);
    CHECK(dcount == 16, "16 errors corrected");
    CHECK(memcmp(block, reference, N) == 0, "block restored bit-exact");

    /* 4. 17 errors exceed the correction capacity */
    corrupt(block, 17);
    dcount = decode_rs_char(rs, block, NULL, 0);
    CHECK(dcount < 0, "17 errors reported uncorrectable");
    memcpy(block, reference, N); /* start over from the clean codeword */

    /* 5. Erasure channel: 2t = 32 declared erasures are corrected */
    {
        int eras_pos[NROOTS];
        int j;
        for (i = 0; i < NROOTS; i++) {
            int pos;
            do {
                pos = (int)(lcg() % N);
                for (j = 0; j < i; j++) {
                    if (eras_pos[j] == pos) break;
                }
            } while (j < i);
            eras_pos[i] = pos;
            block[pos] ^= 0x5A;
        }
        dcount = decode_rs_char(rs, block, eras_pos, NROOTS);
        CHECK(dcount == NROOTS, "32 erasures corrected");
        CHECK(memcmp(block, reference, N) == 0, "erasure decode restores block");
    }
    free_rs_char(rs);

    /* ── int codec: same code, unsigned int symbols ── */
    rs = init_rs_int(8, 0x11d, 1, 1, NROOTS, 0);
    CHECK(rs != NULL, "init_rs_int");
    for (i = 0; i < K; i++) {
        ireference[i] = iblock[i] = lcg() & 0xff;
    }
    encode_rs_int(rs, iblock, iblock + K);
    memcpy(ireference + K, iblock + K, NROOTS * sizeof(unsigned int));
    for (i = 0; i < 8; i++) {
        int pos, j;
        do {
            pos = (int)(lcg() % N);
            for (j = 0; j < i; j++) {
                if (corrupted[j] == pos) break;
            }
        } while (j < i);
        corrupted[i] = pos;
        iblock[pos] ^= 1u + (lcg() & 0x7fu);
    }
    dcount = decode_rs_int(rs, iblock, NULL, 0);
    CHECK(dcount == 8, "int codec corrects 8 errors");
    CHECK(memcmp(iblock, ireference, N * sizeof(unsigned int)) == 0,
          "int codec restores block");
    free_rs_int(rs);

    printf("test_rs: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
