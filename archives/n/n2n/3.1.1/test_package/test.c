/* test_package/test.c — Consumer test for n2n library
 *
 * Tests n2n's pearson hash and wire protocol encode/decode functions.
 * These are self-contained functions that don't require TUN/TAP or network.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>

#include "n2n.h"
#include "n2n_wire.h"

int main(void) {
    int rc = 0;

    /* Test 1: pearson hash init + hash_32 */
    pearson_hash_init();
    const char *data = "hello n2n";
    uint32_t h1 = pearson_hash_32((const uint8_t *)data, strlen(data));
    uint32_t h2 = pearson_hash_32((const uint8_t *)data, strlen(data));
    if (h1 != h2) {
        fprintf(stderr, "FAIL: pearson_hash_32 not deterministic (%u vs %u)\n", h1, h2);
        rc = 1;
    } else {
        printf("PASS: pearson_hash_32 = %u\n", h1);
    }

    /* Test 2: encode/decode uint32 round-trip */
    uint8_t buf[4];
    uint32_t enc_val = 0x12345678;
    size_t enc_idx = 0;
    encode_uint32(buf, &enc_idx, enc_val);
    uint32_t dec_val = 0;
    size_t rem32 = 4;
    size_t dec_idx = 0;
    decode_uint32(&dec_val, buf, &rem32, &dec_idx);
    if (dec_val != enc_val) {
        fprintf(stderr, "FAIL: encode/decode uint32 mismatch (0x%x vs 0x%x)\n", enc_val, dec_val);
        rc = 1;
    } else {
        printf("PASS: encode/decode uint32 = 0x%x\n", dec_val);
    }

    /* Test 3: encode/decode uint16 round-trip */
    uint8_t buf16[2];
    uint16_t enc16 = 0xABCD;
    size_t enc_idx16 = 0;
    encode_uint16(buf16, &enc_idx16, enc16);
    uint16_t dec16 = 0;
    size_t rem16 = 2;
    size_t dec_idx16 = 0;
    decode_uint16(&dec16, buf16, &rem16, &dec_idx16);
    if (dec16 != enc16) {
        fprintf(stderr, "FAIL: encode/decode uint16 mismatch (0x%x vs 0x%x)\n", enc16, dec16);
        rc = 1;
    } else {
        printf("PASS: encode/decode uint16 = 0x%x\n", dec16);
    }

    if (rc == 0) {
        printf("All n2n consumer tests passed.\n");
    }
    return rc;
}
