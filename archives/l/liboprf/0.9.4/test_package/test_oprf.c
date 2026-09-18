/* Consumer test for liboprf 0.9.4 on HarmonyOS.
 *
 * Exercises the real OPRF(ristretto255, SHA-512) API end to end:
 * KeyGen -> Blind -> Evaluate -> Unblind -> Finalize, then checks the two
 * properties a correct OPRF must have: determinism (same key + input gives
 * the same output across independent blindings) and domain separation
 * (different inputs give different outputs). Each check prints one
 * CHECK-OK line; test_package/conanfile.py counts them for the
 * HMBS_TEST_PACKAGE_RESULT marker.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <sodium.h>
#include <oprf/oprf.h>

static int check_roundtrip(const char *label, const uint8_t *input, uint16_t input_len,
                           const uint8_t *other, uint16_t other_len)
{
    uint8_t k[crypto_core_ristretto255_SCALARBYTES];
    uint8_t r[crypto_core_ristretto255_SCALARBYTES];
    uint8_t alpha[crypto_core_ristretto255_BYTES];
    uint8_t beta[crypto_core_ristretto255_BYTES];
    uint8_t n[crypto_core_ristretto255_BYTES];
    uint8_t out[OPRF_BYTES];
    uint8_t out2[OPRF_BYTES];
    uint8_t out_other[OPRF_BYTES];

    oprf_KeyGen(k);
    if (oprf_Blind(input, input_len, r, alpha) != 0) {
        printf("FAIL: %s blind\n", label);
        return 1;
    }
    if (oprf_Evaluate(k, alpha, beta) != 0) {
        printf("FAIL: %s evaluate\n", label);
        return 1;
    }
    if (oprf_Unblind(r, beta, n) != 0) {
        printf("FAIL: %s unblind\n", label);
        return 1;
    }
    if (oprf_Finalize(input, input_len, n, out) != 0) {
        printf("FAIL: %s finalize\n", label);
        return 1;
    }

    /* Determinism: a fresh independent blinding must finalize identically. */
    if (oprf_Blind(input, input_len, r, alpha) != 0 ||
        oprf_Evaluate(k, alpha, beta) != 0 ||
        oprf_Unblind(r, beta, n) != 0 ||
        oprf_Finalize(input, input_len, n, out2) != 0) {
        printf("FAIL: %s second pass\n", label);
        return 1;
    }
    if (memcmp(out, out2, OPRF_BYTES) != 0) {
        printf("FAIL: %s not deterministic\n", label);
        return 1;
    }

    /* Domain separation: a different input must give a different output. */
    if (oprf_Blind(other, other_len, r, alpha) != 0 ||
        oprf_Evaluate(k, alpha, beta) != 0 ||
        oprf_Unblind(r, beta, n) != 0 ||
        oprf_Finalize(other, other_len, n, out_other) != 0) {
        printf("FAIL: %s other-input pass\n", label);
        return 1;
    }
    if (memcmp(out, out_other, OPRF_BYTES) == 0) {
        printf("FAIL: %s inputs collide\n", label);
        return 1;
    }

    sodium_memzero(k, sizeof k);
    sodium_memzero(r, sizeof r);
    printf("CHECK-OK: %s\n", label);
    return 0;
}

int main(void)
{
    static const uint8_t input_a[] = "harmonyos-oprf-test";
    static const uint8_t input_b[] = "harmonyos-oprf-other";
    static const uint8_t input_c[] = "threshold-oprf-vector-2";
    static const uint8_t input_d[] = "threshold-oprf-other-2";
    int fails = 0;

    if (sodium_init() < 0) {
        printf("FAIL: sodium_init\n");
        return 1;
    }

    fails += check_roundtrip("basic-roundtrip",
                             input_a, (uint16_t)(sizeof input_a - 1),
                             input_b, (uint16_t)(sizeof input_b - 1));
    fails += check_roundtrip("second-vector",
                             input_c, (uint16_t)(sizeof input_c - 1),
                             input_d, (uint16_t)(sizeof input_d - 1));

    if (fails == 0) {
        printf("liboprf consumer test passed: 2/2 checks\n");
        return 0;
    }
    printf("liboprf consumer test failed: %d check(s)\n", fails);
    return 1;
}
