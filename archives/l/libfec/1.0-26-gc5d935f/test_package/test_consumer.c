/* test_consumer.c — consumer use case for the packaged libfec.
 *
 * Simulates the classic concatenated-FEC downlink this library was built
 * for (CCSDS-style): a 223-byte payload is protected by an RS(255,223)
 * outer code, the whole codeword is convolutionally encoded (K=7, r=1/2,
 * the polynomials from fec.h) as the inner code, sent over a soft-symbol
 * channel, Viterbi-decoded, repacked into the received codeword, and
 * finally RS-decoded with injected residual byte errors. This chains all
 * three subsystems (RS codec, Viterbi decoder, parity helpers from fec.h)
 * exactly the way a real consumer would.
 *
 * Chainback format note (matches upstream vtest27): the decoder returns
 * the encoder shift-register history; with the encoder loop
 * `sr = (sr << 1) | bit; bits[i/8] = sr & 0xff;` the history bytes are
 * already MSB-first packed original bits — no bit reversal is needed.
 */
#include <stdio.h>
#include <string.h>

#include "fec.h"

#define NROOTS 32
#define N 255
#define K (N - NROOTS)   /* 223 */
#define FRAMEBITS (N * 8) /* 2040 */

static unsigned long lcg_state = 0x1234cafeUL;
static unsigned int lcg(void)
{
    lcg_state = lcg_state * 1103515245UL + 12345UL;
    return (unsigned int)((lcg_state >> 16) & 0x7fff);
}

static unsigned char payload[K];    /* original plaintext */
static unsigned char codeword[N];   /* RS codeword sent */
static unsigned char symbols[2 * (FRAMEBITS + 6)];
static unsigned char vdata[FRAMEBITS / 8 + 1];
static unsigned char received[N];
static int erasdedup[N];

int main(void)
{
    int i, j, dcount;
    int checks = 0, failures = 0;
    void *rs, *vp;
    int sr = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        checks++;                                                           \
        if (!(cond)) {                                                      \
            failures++;                                                     \
            printf("FAIL %s:%d %s\n", __FILE__, __LINE__, msg);             \
        }                                                                   \
    } while (0)

    /* ── outer code: RS(255,223) over GF(256) ── */
    rs = init_rs_char(8, 0x11d, 1, 1, NROOTS, 0);
    CHECK(rs != NULL, "init_rs_char");
    for (i = 0; i < K; i++) {
        payload[i] = (unsigned char)lcg();
    }
    memcpy(codeword, payload, K);
    encode_rs_char(rs, codeword, codeword + K);

    /* ── inner code: K=7 r=1/2 convolutional, 6-bit zero tail ── */
    vp = create_viterbi27(FRAMEBITS);
    CHECK(vp != NULL, "create_viterbi27");
    for (i = 0; i < FRAMEBITS + 6; i++) {
        int bit;
        if (i < FRAMEBITS) {
            bit = (codeword[i / 8] >> (7 - (i % 8))) & 1; /* MSB first */
        } else {
            bit = 0; /* tail flush to state 0 */
        }
        sr = (sr << 1) | bit;
        symbols[2 * i + 0] = parity(sr & V27POLYA) ? 255 : 0;
        symbols[2 * i + 1] = parity(sr & V27POLYB) ? 255 : 0;
    }
    init_viterbi27(vp, 0);
    update_viterbi27_blk(vp, symbols, FRAMEBITS + 6);
    chainback_viterbi27(vp, vdata, FRAMEBITS, 0);
    delete_viterbi27(vp);

    /* unpack: chainback history bytes are already MSB-first packed bits */
    memcpy(received, vdata, N);
    CHECK(memcmp(received, codeword, N) == 0,
          "clean channel: Viterbi roundtrip reproduces the RS codeword");

    /* ── residual channel errors on the decoded codeword: t = 16 bytes ── */
    for (i = 0; i < 16; i++) {
        int pos;
        do {
            pos = (int)(lcg() % N);
            for (j = 0; j < i; j++) {
                if (erasdedup[j] == pos) break;
            }
        } while (j < i);
        erasdedup[i] = pos;
        received[pos] ^= (unsigned char)(1u + lcg() % 255u);
    }
    dcount = decode_rs_char(rs, received, NULL, 0);
    CHECK(dcount == 16, "RS decoder corrects the 16 residual byte errors");
    CHECK(memcmp(received, payload, K) == 0,
          "concatenated chain recovers the original 223-byte payload");
    free_rs_char(rs);

    printf("test_consumer: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
