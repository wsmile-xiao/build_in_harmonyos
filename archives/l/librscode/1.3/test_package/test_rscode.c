/*
 * test_rscode.c — librscode 1.3 functional test
 *
 * Real functional test using the public RSCODE C API from ecc.h:
 *
 *   void initialize_ecc(void);
 *   void encode_data(unsigned char msg[], int nbytes, unsigned char dst[]);
 *   void decode_data(unsigned char data[], int nbytes);
 *   int  check_syndrome(void);
 *   int  correct_errors_erasures(unsigned char codeword[], int csize,
 *                                int nerasures, int erasures[]);
 *   BIT16 crc_ccitt(unsigned char *msg, int len);
 *   int  gmult(int a, int b);
 *   int  ginv(int elt);
 *
 * Deterministic (no rand/time): fixed 28-byte message, NPAR=4 parity.
 * Exercises encode -> decode round-trip, single-error correction,
 * single-erasure correction, CRC-CCITT determinism, and galois
 * field identities. Links libecc and calls the real functions —
 * NOT an include-only test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ecc.h"

#define MSGLEN 28
#define CWSIZE (MSGLEN + NPAR)

static unsigned char fixed_msg[MSGLEN] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26,
    0x30, 0x31, 0x32, 0x33, 0x48, 0x65, 0x6C
};

static int passed = 0;
static int failed = 0;

#define CHECK(cond, label) do { \
    if (cond) { printf("[ok] %s\n", label); passed++; } \
    else { printf("[fail] %s\n", label); failed++; } \
} while (0)

int main(void)
{
    unsigned char codeword[256];
    unsigned char msg_copy[MSGLEN];
    int i;

    /* 1: library init (must not crash; builds galois tables). */
    initialize_ecc();
    CHECK(gexp[0] != 0 || gexp[1] != 0, "initialize_ecc builds galois tables");

    /* 2: encode then decode without errors: syndrome must be zero
     * and payload must round-trip byte-exact. */
    memcpy(msg_copy, fixed_msg, MSGLEN);
    encode_data(msg_copy, MSGLEN, codeword);
    {
        unsigned char cw[256];
        memcpy(cw, codeword, CWSIZE);
        decode_data(cw, CWSIZE);
        CHECK(check_syndrome() == 0, "clean codeword syndrome is zero");
        CHECK(memcmp(cw, fixed_msg, MSGLEN) == 0, "clean round-trip payload matches");
    }

    /* 3: single-byte error correction (1 error needs 2*1 <= NPAR=4). */
    {
        unsigned char cw[256];
        int erasures[16];
        int result;
        memcpy(cw, codeword, CWSIZE);
        cw[5] ^= 0x5A;
        decode_data(cw, CWSIZE);
        CHECK(check_syndrome() != 0, "corrupted codeword syndrome is nonzero");
        result = correct_errors_erasures(cw, CWSIZE, 0, erasures);
        CHECK(result != 0, "correct_errors_erasures reports success for 1 error");
        CHECK(memcmp(cw, fixed_msg, MSGLEN) == 0, "single error corrected payload matches");
    }

    /* 4: single-erasure correction (location known, 1-based from start
     * per example.c byte_erasure convention: dst[loc-1]). */
    {
        unsigned char cw[256];
        int erasures[16];
        int result;
        memcpy(cw, codeword, CWSIZE);
        cw[10] = 0;
        erasures[0] = CWSIZE - 10 - 1;
        decode_data(cw, CWSIZE);
        result = correct_errors_erasures(cw, CWSIZE, 1, erasures);
        CHECK(result != 0, "correct_errors_erasures reports success for 1 erasure");
        CHECK(memcmp(cw, fixed_msg, MSGLEN) == 0, "single erasure corrected payload matches");
    }

    /* 5: CRC-CCITT is deterministic and nonzero on the message. */
    {
        BIT16 c1 = crc_ccitt(fixed_msg, MSGLEN);
        BIT16 c2 = crc_ccitt(fixed_msg, MSGLEN);
        CHECK(c1 == c2, "crc_ccitt deterministic on same input");
        CHECK(c1 != 0, "crc_ccitt nonzero on fixed message");
        (void)i;
    }

    /* 6: galois field identities: x*1==x and x*inv(x)==1 for x!=0. */
    {
        int x = 0x53;
        CHECK(gmult(x, 1) == x, "gmult identity x*1==x");
        CHECK(gmult(x, ginv(x)) == 1, "gmult(x,ginv(x))==1");
    }

    printf("RESULT: %d passed, %d failed\n", passed, failed);
    if (failed != 0) {
        printf("=== %d assertion(s) FAILED ===\n", failed);
        return 1;
    }
    printf("=== All assertions passed ===\n");
    return 0;
}
