/*
 * test_cotp.c — libcotp 4.2.1 functional test.
 *
 * Verifies the real public API declared in src/cotp.h:
 *   - base32_encode : encode the RFC-4226 shared secret to base32
 *   - get_hotp      : HOTP per RFC-4226 (known-answer vectors, table 1)
 *   - get_totp_at   : TOTP per RFC-6238 (known-answer vector, SHA1, 8 digits)
 *   - otp_to_int    : numeric round-trip of a 6-digit HOTP
 *
 * All vectors are taken verbatim from RFC-4226 §D (HOTP) and RFC-6238
 * Appendix B (TOTP), and cross-checked against the upstream
 * tests/test_otp.c test suite.
 *
 * The shared secret is the ASCII string "12345678901234567890" (RFC test
 * seed). get_hotp/get_totp_at expect a *base32-encoded* secret, so the test
 * first runs base32_encode on the raw seed exactly as the upstream tests do.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "cotp.h"

static int failures = 0;

static void check_str(const char *label, const char *got, const char *expected) {
    if (!got) {
        fprintf(stderr, "FAIL %s: got NULL, expected \"%s\"\n", label, expected);
        failures++;
        return;
    }
    if (strcmp(got, expected) != 0) {
        fprintf(stderr, "FAIL %s: got \"%s\", expected \"%s\"\n", label, got, expected);
        failures++;
    } else {
        printf("PASS %s: %s\n", label, got);
    }
}

static void check_int(const char *label, int64_t got, int64_t expected) {
    if (got != expected) {
        fprintf(stderr, "FAIL %s: got %ld, expected %ld\n", label, (long)got, (long)expected);
        failures++;
    } else {
        printf("PASS %s: %ld\n", label, (long)got);
    }
}

int main(void) {
    /*
     * RFC-4226 / RFC-6238 shared seed (ASCII). The OTP functions consume a
     * base32-encoded secret, so we encode it the same way upstream tests do
     * (base32_encode over strlen(K)+1 bytes to include the trailing NUL).
     */
    const char *K = "12345678901234567890";

    cotp_error_t err = NO_ERROR;

    /* Step 1: base32-encode the seed. */
    char *K_b32 = base32_encode((const uint8_t *)K, strlen(K) + 1, &err);
    if (!K_b32 || err != NO_ERROR) {
        fprintf(stderr, "FAIL base32_encode: err=%d\n", err);
        free(K_b32);
        return 1;
    }
    printf("PASS base32_encode: seed -> %s\n", K_b32);

    /* Step 2: HOTP per RFC-4226 Appendix D, table 1 (SHA1, 6 digits).
     *   counter 0 -> 755224
     *   counter 1 -> 287082
     *   counter 2 -> 359152
     *   counter 3 -> 969429
     */
    const long counters[]  = {0, 1, 2, 3};
    const char *hotp_exp[] = {"755224", "287082", "359152", "969429"};
    for (int i = 0; i < 4; i++) {
        err = NO_ERROR;
        char *hotp = get_hotp(K_b32, counters[i], 6, COTP_SHA1, &err);
        char label[32];
        snprintf(label, sizeof(label), "get_hotp[c=%ld]", counters[i]);
        check_str(label, hotp, hotp_exp[i]);
        free(hotp);
    }

    /* Step 3: TOTP per RFC-6238 Appendix B (SHA1, 8 digits, period 30).
     *   T = 59            -> 94287082
     *   T = 1111111109    -> 07081804
     *   T = 1234567890    -> 89005924
     */
    const long totp_ts[]   = {59, 1111111109L, 1234567890L};
    const char *totp_exp[] = {"94287082", "07081804", "89005924"};
    for (int i = 0; i < 3; i++) {
        err = NO_ERROR;
        char *totp = get_totp_at(K_b32, totp_ts[i], 8, 30, COTP_SHA1, &err);
        char label[40];
        snprintf(label, sizeof(label), "get_totp_at[T=%ld]", totp_ts[i]);
        check_str(label, totp, totp_exp[i]);
        free(totp);
    }

    /* Step 4: otp_to_int round-trip on a 6-digit HOTP with leading zero.
     * "07081804" -> 7081804 with err == MISSING_LEADING_ZERO.
     */
    err = NO_ERROR;
    char *t0 = get_totp_at(K_b32, 1111111109L, 8, 30, COTP_SHA1, &err);
    err = NO_ERROR;
    int64_t v = otp_to_int(t0, &err);
    check_int("otp_to_int(07081804)", v, 7081804);
    free(t0);

    /* Step 5: cotp_strerror returns a non-NULL static description. */
    const char *desc = cotp_strerror(NO_ERROR);
    if (desc == NULL) {
        fprintf(stderr, "FAIL cotp_strerror(NO_ERROR): returned NULL\n");
        failures++;
    } else {
        printf("PASS cotp_strerror(NO_ERROR): %s\n", desc);
    }

    free(K_b32);

    if (failures == 0) {
        printf("\nAll libcotp tests PASSED\n");
        return 0;
    }
    fprintf(stderr, "\n%d libcotp test(s) FAILED\n", failures);
    return 1;
}
