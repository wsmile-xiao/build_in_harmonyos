/*
 * Consumer test for libbaseencode 1.0.15.
 * Exercises the public API (base32_encode/base32_decode/base64_encode/
 * base64_decode) with RFC-4648 vectors and verifies round-trip results.
 * R34: must actually call the package API and validate observable output.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <baseencode.h>

static int failures = 0;

static void check_b64_roundtrip(const unsigned char *data, size_t len)
{
    baseencode_error_t err;
    char *enc = base64_encode(data, len, &err);
    if (enc == NULL || err != SUCCESS) {
        printf("FAIL: base64_encode len=%zu err=%d\n", len, (int)err);
        failures++;
        return;
    }
    unsigned char *dec = base64_decode(enc, strlen(enc) + 1, &err);
    if (dec == NULL || err != SUCCESS) {
        printf("FAIL: base64_decode err=%d\n", (int)err);
        failures++;
    } else if (memcmp(dec, data, len) != 0) {
        printf("FAIL: base64 round-trip mismatch len=%zu\n", len);
        failures++;
    } else {
        printf("PASS: base64 round-trip len=%zu -> \"%s\"\n", len, enc);
    }
    free(enc);
    free(dec);
}

static void check_b32_roundtrip(const unsigned char *data, size_t len)
{
    baseencode_error_t err;
    char *enc = base32_encode(data, len, &err);
    if (enc == NULL || err != SUCCESS) {
        printf("FAIL: base32_encode len=%zu err=%d\n", len, (int)err);
        failures++;
        return;
    }
    unsigned char *dec = base32_decode(enc, strlen(enc) + 1, &err);
    if (dec == NULL || err != SUCCESS) {
        printf("FAIL: base32_decode err=%d\n", (int)err);
        failures++;
    } else if (memcmp(dec, data, len) != 0) {
        printf("FAIL: base32 round-trip mismatch len=%zu\n", len);
        failures++;
    } else {
        printf("PASS: base32 round-trip len=%zu -> \"%s\"\n", len, enc);
    }
    free(enc);
    free(dec);
}

int main(void)
{
    /* RFC-4648 test vector: "foobar" (6 bytes, no padding needed decisions are internal) */
    static const unsigned char v1[] = "foobar";
    static const unsigned char v2[] = "Hello, HarmonyOS!";
    /* Binary bytes without embedded NUL (libbaseencode treats input as a
     * NUL-terminated C string: an embedded 0x00 truncates the input). */
    static const unsigned char v3[] = {0x41, 0x42, 0x43, 0x7f, 0x80, 0xff};

    check_b64_roundtrip(v1, sizeof(v1) - 1);
    check_b32_roundtrip(v1, sizeof(v1) - 1);
    check_b64_roundtrip(v2, sizeof(v2) - 1);
    check_b32_roundtrip(v2, sizeof(v2) - 1);
    check_b64_roundtrip(v3, sizeof(v3));
    check_b32_roundtrip(v3, sizeof(v3));

    if (failures > 0) {
        printf("test_libbaseencode: %d FAILURES\n", failures);
        return 1;
    }
    printf("test_libbaseencode: all round-trip checks passed\n");
    return 0;
}