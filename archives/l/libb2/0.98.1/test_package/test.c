/*
 * test_package/test.c — libb2 consumer test
 * Verifies blake2b hash of empty input matches known answer (KAT)
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "blake2.h"

int main(void) {
    /* Known answer: blake2b hash of 0 bytes (no key, full 64-byte output) */
    static const uint8_t expected[BLAKE2B_OUTBYTES] = {
        0x78, 0x6A, 0x02, 0xF7, 0x42, 0x01, 0x59, 0x03,
        0xC6, 0xC6, 0xFD, 0x85, 0x25, 0x52, 0xD2, 0x72,
        0x91, 0x2F, 0x47, 0x40, 0xE1, 0x58, 0x47, 0x61,
        0x8A, 0x86, 0xE2, 0x17, 0xF7, 0x1F, 0x54, 0x19,
        0xD2, 0x5E, 0x10, 0x31, 0xAF, 0xEE, 0x58, 0x53,
        0x13, 0x89, 0x64, 0x44, 0x93, 0x4E, 0xB0, 0x4B,
        0x90, 0x3A, 0x68, 0x5B, 0x14, 0x48, 0xB7, 0x55,
        0xD5, 0x6F, 0x70, 0x1A, 0xFE, 0x9B, 0xE2, 0xCE
    };

    uint8_t hash[BLAKE2B_OUTBYTES];

    /* One-shot blake2b of empty input (no key) */
    int ret = blake2b(hash, "", NULL, BLAKE2B_OUTBYTES, 0, 0);
    if (ret != 0) {
        fprintf(stderr, "blake2b() returned %d\n", ret);
        return 1;
    }

    /* Verify against known answer */
    if (memcmp(hash, expected, BLAKE2B_OUTBYTES) != 0) {
        fprintf(stderr, "blake2b hash mismatch!\n");
        return 1;
    }

    /* Also test incremental API with "abc" */
    blake2b_state state;
    if (blake2b_init(&state, BLAKE2B_OUTBYTES) != 0) {
        fprintf(stderr, "blake2b_init failed\n");
        return 1;
    }
    blake2b_update(&state, (const uint8_t *)"abc", 3);
    uint8_t hash2[BLAKE2B_OUTBYTES];
    blake2b_final(&state, hash2, BLAKE2B_OUTBYTES);

    /* One-shot should match incremental for same input */
    uint8_t hash3[BLAKE2B_OUTBYTES];
    blake2b(hash3, "abc", NULL, BLAKE2B_OUTBYTES, 3, 0);
    if (memcmp(hash2, hash3, BLAKE2B_OUTBYTES) != 0) {
        fprintf(stderr, "incremental vs one-shot mismatch!\n");
        return 1;
    }

    printf("libb2 test: PASS (blake2b KAT verified, incremental API verified)\n");
    return 0;
}
