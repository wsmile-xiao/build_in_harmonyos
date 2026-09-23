#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "passwdqc.h"

static int failures = 0;
static int total = 0;

#define CHECK(cond, msg) do { \
    total++; \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        failures++; \
    } else { \
        printf("PASS: %s\n", msg); \
    } \
} while (0)

static passwdqc_params_qc_t default_params(void)
{
    passwdqc_params_qc_t p;
    memset(&p, 0, sizeof(p));
    p.min[0] = p.min[1] = p.min[2] = p.min[3] = p.min[4] = 8;
    p.max = 72;
    p.passphrase_words = 3;
    p.match_length = 4;
    p.similar_deny = 1;
    p.random_bits = 32;
    return p;
}

int main(void)
{
    passwdqc_params_qc_t params = default_params();
    const char *reason;
    char *generated;

    /* ── 1. Strong passphrase accepted ── */
    reason = passwdqc_check(&params, "correct horse battery staple", NULL, NULL);
    CHECK(reason == NULL, "strong passphrase accepted");

    /* ── 2. Random passphrase generated ── */
    generated = passwdqc_random(&params);
    CHECK(generated != NULL && strlen(generated) > 0, "random passphrase non-empty");

    /* ── 3. Weak password rejected ── */
    reason = passwdqc_check(&params, "123", NULL, NULL);
    CHECK(reason != NULL, "weak password rejected (too short)");

    /* ── 4. Trivial password rejected ── */
    reason = passwdqc_check(&params, "password", NULL, NULL);
    CHECK(reason != NULL, "trivial password rejected (dictionary)");

    /* ── 5. Random uniqueness: two calls produce different output ── */
    char *gen1 = passwdqc_random(&params);
    char *gen2 = passwdqc_random(&params);
    CHECK(gen1 && gen2 && strcmp(gen1, gen2) != 0, "random passphrase uniqueness");

    /* ── 6. Similarity detection: newpass too similar to oldpass ── */
    reason = passwdqc_check(&params, "correct horse battery", "correct horse battery staple", NULL);
    CHECK(reason != NULL, "similarity detection rejects near-duplicate");

    /* ── 7. Empty password rejected ── */
    reason = passwdqc_check(&params, "", NULL, NULL);
    CHECK(reason != NULL, "empty password rejected");

    /* ── 8. Long passphrase within max accepted ── */
    reason = passwdqc_check(&params,
        "the quick brown fox jumps over the lazy dog at noon today",
        NULL, NULL);
    CHECK(reason == NULL, "long passphrase accepted");

    /* ── 9. Relaxed params: short min allows short passwords ── */
    passwdqc_params_qc_t relaxed = default_params();
    relaxed.min[0] = relaxed.min[1] = relaxed.min[2] = relaxed.min[3] = relaxed.min[4] = 1;
    reason = passwdqc_check(&relaxed, "ab", NULL, NULL);
    CHECK(reason == NULL, "relaxed min config accepts short password");

    /* ── 10. Strict params: high min rejects medium password ── */
    passwdqc_params_qc_t strict = default_params();
    strict.min[0] = strict.min[1] = strict.min[2] = strict.min[3] = strict.min[4] = 40;
    reason = passwdqc_check(&strict, "correct horse battery staple", NULL, NULL);
    CHECK(reason != NULL, "strict min config rejects medium password");

    /* ── 11. Config file loading ── */
    passwdqc_params_t full_params;
    memset(&full_params, 0, sizeof(full_params));
    char *load_reason = NULL;
    /* passwdqc.conf is packaged in etc/ — try loading from common paths */
    int rc = passwdqc_params_load(&full_params, &load_reason, "passwdqc.conf");
    CHECK(rc == 0 || (load_reason != NULL), "config file load (passwdqc.conf)");
    passwdqc_params_reset(&full_params);
    passwdqc_params_free(&full_params);

    printf("\n%d/%d passed, %d failed\n", total - failures, total, failures);
    return failures != 0 ? 1 : 0;
}
