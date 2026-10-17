#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "libsais.h"

/* Expected suffix array of "banana" (6 bytes, no NUL terminator) computed from
 * the sorted suffixes: a(5) < ana(3) < anana(1) < banana(0) < na(4) < nana(2).
 * Verified against the upstream 2.10.4 build before writing this test. */
static const int32_t EXPECTED_SA[6] = {5, 3, 1, 0, 4, 2};

/* Expected Burrows-Wheeler transform of "banana". Verified against upstream
 * libsais_bwt(): primary=4, output "annbaa". */
static const char EXPECTED_BWT[6] = {'a', 'n', 'n', 'b', 'a', 'a'};

int main(void) {
    const char *text = "banana";
    int32_t n = (int32_t)strlen(text);
    int32_t SA[6] = {0};
    int32_t freq[256] = {0};

    /* --- Test 1: suffix array construction (core libsais API) --- */
    int32_t ret = libsais((const uint8_t *)text, SA, n, 0, freq);
    if (ret != 0) {
        fprintf(stderr, "FAIL: libsais() returned %d, expected 0\n", ret);
        return 1;
    }
    for (int32_t i = 0; i < n; i++) {
        if (SA[i] != EXPECTED_SA[i]) {
            fprintf(stderr, "FAIL: SA[%d]=%d, expected %d\n", i, SA[i], EXPECTED_SA[i]);
            return 1;
        }
    }
    printf("PASS libsais suffix array: ");
    for (int32_t i = 0; i < n; i++) printf("%d ", SA[i]);
    printf("\n");

    /* --- Test 2: context-based suffix array (libsais_ctx) --- */
    int32_t SA2[6] = {0};
    void *ctx = libsais_create_ctx();
    if (ctx == NULL) {
        fprintf(stderr, "FAIL: libsais_create_ctx() returned NULL\n");
        return 1;
    }
    ret = libsais_ctx(ctx, (const uint8_t *)text, SA2, n, 0, NULL);
    libsais_free_ctx(ctx);
    if (ret != 0) {
        fprintf(stderr, "FAIL: libsais_ctx() returned %d, expected 0\n", ret);
        return 1;
    }
    for (int32_t i = 0; i < n; i++) {
        if (SA2[i] != EXPECTED_SA[i]) {
            fprintf(stderr, "FAIL: ctx SA[%d]=%d, expected %d\n", i, SA2[i], EXPECTED_SA[i]);
            return 1;
        }
    }
    printf("PASS libsais_ctx suffix array (context reused)\n");

    /* --- Test 3: Burrows-Wheeler transform (libsais_bwt) --- */
    uint8_t bwt[6] = {0};
    int32_t A[6] = {0};
    int32_t primary = libsais_bwt((const uint8_t *)text, bwt, A, n, 0, NULL);
    if (primary < 0) {
        fprintf(stderr, "FAIL: libsais_bwt() returned %d\n", primary);
        return 1;
    }
    for (int32_t i = 0; i < n; i++) {
        if (bwt[i] != (uint8_t)EXPECTED_BWT[i]) {
            fprintf(stderr, "FAIL: BWT[%d]=%c, expected %c\n", i, bwt[i], EXPECTED_BWT[i]);
            return 1;
        }
    }
    printf("PASS libsais_bwt (primary=%d, output=\"%.*s\")\n", primary, n, bwt);

    /* --- Test 4: version sanity --- */
    if (LIBSAIS_VERSION_MAJOR != 2 || LIBSAIS_VERSION_MINOR != 10 || LIBSAIS_VERSION_PATCH != 4) {
        fprintf(stderr, "FAIL: unexpected version %d.%d.%d\n",
                LIBSAIS_VERSION_MAJOR, LIBSAIS_VERSION_MINOR, LIBSAIS_VERSION_PATCH);
        return 1;
    }
    printf("PASS libsais version %s\n", LIBSAIS_VERSION_STRING);

    printf("libsais 2.10.4 API test: OK\n");
    return 0;
}
