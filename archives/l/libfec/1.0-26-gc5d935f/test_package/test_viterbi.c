/* test_viterbi.c — K=7 r=1/2 Viterbi consumer test for the packaged libfec.
 *
 * Convolves a deterministic pseudo-random frame with the CCSDS polynomials
 * from fec.h (V27POLYA=0x6d, V27POLYB=0x4f) on a noise-free soft channel
 * (symbols 0/255), appends the 6-bit zero tail like upstream vtest27, then
 * decodes with create/init/update/chainback and requires a bit-exact match.
 * The encoder/decoder calling sequence mirrors upstream vtest27.c.
 */
#include <stdio.h>
#include <string.h>

#include "fec.h"

#define FRAMEBITS 1024
#define SYMCNT (2 * (FRAMEBITS + 6))

static unsigned long lcg_state = 0xfec01fecUL;
static unsigned int lcg(void)
{
    lcg_state = lcg_state * 1103515245UL + 12345UL;
    return (unsigned int)((lcg_state >> 16) & 1u);
}

static unsigned char bits[(FRAMEBITS + 6) / 8 + 1];
static unsigned char data[FRAMEBITS / 8];
static unsigned char symbols[SYMCNT];

int main(void)
{
    int i;
    int failures = 0;
    int checks = 0;
    int sr = 0;
    void *vp;

    vp = create_viterbi27(FRAMEBITS);
    checks++;
    if (vp == NULL) {
        printf("FAIL create_viterbi27 returned NULL\n");
        return 1;
    }

    /* Encode FRAMEBITS payload bits plus a 6-bit flush-to-zero tail */
    for (i = 0; i < FRAMEBITS + 6; i++) {
        int bit = (i < FRAMEBITS) ? (int)lcg() : 0;
        sr = (sr << 1) | bit;
        bits[i / 8] = sr & 0xff;
        /* Noise-free soft symbols: bit 1 -> 255, bit 0 -> 0 */
        symbols[2 * i + 0] = parity(sr & V27POLYA) ? 255 : 0;
        symbols[2 * i + 1] = parity(sr & V27POLYB) ? 255 : 0;
    }

    init_viterbi27(vp, 0);
    if (update_viterbi27_blk(vp, symbols, FRAMEBITS + 6) == 0) {
        checks++;
    } else {
        checks++;
        failures++;
        printf("FAIL update_viterbi27_blk returned error\n");
    }
    /* The encoder was flushed to state 0 by the 6 zero tail bits */
    chainback_viterbi27(vp, data, FRAMEBITS, 0);

    checks++;
    if (memcmp(data, bits, FRAMEBITS / 8) != 0) {
        int errbits = 0;
        failures++;
        for (i = 0; i < FRAMEBITS / 8; i++) {
            errbits += Bitcnt[(unsigned char)(data[i] ^ bits[i])];
        }
        printf("FAIL viterbi27 chainback: %d bit errors in %d bits\n",
               errbits, FRAMEBITS);
    }

    delete_viterbi27(vp);
    printf("test_viterbi: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
