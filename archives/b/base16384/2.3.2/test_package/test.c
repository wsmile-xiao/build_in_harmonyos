/*
 * test_package for base16384: roundtrip encode/decode verification.
 *
 * Tests base16384_encode + base16384_decode roundtrip on a known payload,
 * and verifies the decoded output matches the original input byte-for-byte.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "base16384.h"

int main(void)
{
    /* A well-known payload that includes edge-relevant lengths. */
    const char *payload = "Hello, base16384! This is a Conan test_package verification.";
    const int payload_len = (int)strlen(payload);

    /* Encode: output buffer must be >= base16384_encode_len(payload_len). */
    int encbuf_sz = base16384_encode_len(payload_len);
    char *encbuf = (char *)malloc(encbuf_sz);
    if (!encbuf) {
        fprintf(stderr, "malloc encbuf failed\n");
        return 1;
    }

    int encoded_len = base16384_encode(payload, payload_len, encbuf);
    if (encoded_len <= 0) {
        fprintf(stderr, "base16384_encode returned %d\n", encoded_len);
        free(encbuf);
        return 1;
    }

    /* Decode: output buffer must be >= base16384_decode_len(encoded_len, 0). */
    int decbuf_sz = base16384_decode_len(encoded_len, 0);
    char *decbuf = (char *)malloc(decbuf_sz);
    if (!decbuf) {
        fprintf(stderr, "malloc decbuf failed\n");
        free(encbuf);
        return 1;
    }

    int decoded_len = base16384_decode(encbuf, encoded_len, decbuf);
    if (decoded_len != payload_len) {
        fprintf(stderr, "decoded length mismatch: expected %d, got %d\n",
                payload_len, decoded_len);
        free(encbuf);
        free(decbuf);
        return 1;
    }

    if (memcmp(payload, decbuf, payload_len) != 0) {
        fprintf(stderr, "roundtrip data mismatch\n");
        free(encbuf);
        free(decbuf);
        return 1;
    }

    printf("base16384 test_package PASSED: roundtrip %d bytes -> %d encoded -> %d decoded\n",
           payload_len, encoded_len, decoded_len);

    free(encbuf);
    free(decbuf);
    return 0;
}
