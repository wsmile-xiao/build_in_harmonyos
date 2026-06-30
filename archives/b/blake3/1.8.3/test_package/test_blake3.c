/*
 * test_blake3.c — Simple BLAKE3 hash test using official test vectors.
 *
 * Verifies that:
 *   1. blake3_version() returns "1.8.3"
 *   2. Hash of empty input matches official test vector
 *   3. Hash of "hello" matches known value
 */
#include "blake3.h"
#include <stdio.h>
#include <string.h>

/* Helper: convert hex string to byte array */
static int hex_to_bytes(const char *hex, uint8_t *out, size_t out_len) {
    for (size_t i = 0; i < out_len; i++) {
        unsigned int byte;
        if (sscanf(hex + 2 * i, "%2x", &byte) != 1)
            return -1;
        out[i] = (uint8_t)byte;
    }
    return 0;
}

/* Helper: compare and print hash result */
static int check_hash(const char *label, const uint8_t *got,
                      const char *expected_hex) {
    uint8_t expected[BLAKE3_OUT_LEN];
    if (hex_to_bytes(expected_hex, expected, BLAKE3_OUT_LEN) != 0) {
        fprintf(stderr, "FAIL: %s — invalid expected hex\n", label);
        return 1;
    }
    if (memcmp(got, expected, BLAKE3_OUT_LEN) != 0) {
        fprintf(stderr, "FAIL: %s — hash mismatch\n", label);
        fprintf(stderr, "  got:      ");
        for (int i = 0; i < BLAKE3_OUT_LEN; i++)
            fprintf(stderr, "%02x", got[i]);
        fprintf(stderr, "\n  expected: %s\n", expected_hex);
        return 1;
    }
    printf("PASS: %s\n", label);
    return 0;
}

int main(void) {
    int failures = 0;

    /* Test 1: Version string */
    const char *ver = blake3_version();
    if (strcmp(ver, "1.8.3") != 0) {
        fprintf(stderr, "FAIL: version is \"%s\", expected \"1.8.3\"\n", ver);
        failures++;
    } else {
        printf("PASS: blake3_version() = \"%s\"\n", ver);
    }

    /* Test 2: Hash of empty input (from official test_vectors.json, input_len=0) */
    blake3_hasher hasher;
    uint8_t out[BLAKE3_OUT_LEN];

    blake3_hasher_init(&hasher);
    blake3_hasher_finalize(&hasher, out, BLAKE3_OUT_LEN);
    failures += check_hash("hash of empty input", out,
        "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262");

    /* Test 3: Hash of single byte 0x00 (from official test_vectors.json, input_len=1) */
    blake3_hasher_init(&hasher);
    uint8_t zero = 0;
    blake3_hasher_update(&hasher, &zero, 1);
    blake3_hasher_finalize(&hasher, out, BLAKE3_OUT_LEN);
    failures += check_hash("hash of 0x00", out,
        "2d3adedff11b61f14c886e35afa036736dcd87a74d27b5c1510225d0f592e213");

    if (failures > 0) {
        fprintf(stderr, "\n%d test(s) FAILED\n", failures);
        return 1;
    }

    printf("\nAll blake3 tests passed.\n");
    return 0;
}
