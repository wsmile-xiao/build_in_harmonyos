/* test_package for lib25519 0-20260614 — consumer-side API contract test.
 *
 * Contract source: upstream doc/api.md (stable C API = 5 functions) and the
 * generated include/lib25519.h Macros:
 *   X25519: lib25519_dh_keypair(pk,sk), lib25519_dh(k,pk,sk)
 *   Ed25519: lib25519_sign_keypair(pk,sk), lib25519_sign(sm,&smlen,m,mlen,sk),
 *            lib25519_sign_open(m,&mlen,sm,smlen,pk) -> 0 on success
 *
 * What is deliberately NOT asserted (not guaranteed by the API):
 *   - exact key/signature bytes (randomized key generation);
 *   - byte-equality of two signatures over the same message (the stable
 *     C API does not guarantee deterministic signing; upstream KATs stub
 *     randombytes deterministically so they cannot observe real-entropy
 *     behavior either — repeated signs must each verify, not match);
 *   - signature malleability details beyond open() accept/reject;
 *   - which implementation backend was selected at build time;
 *   - timing or performance properties.
 *
 * Falsifiability: checks 2/3 fail if key generation is broken or
 * deterministic-stubbed (two keypairs must differ); checks 3/6 fail if
 * DH/sign math is wrong; checks 7/8 fail if verification always accepts
 * (tamper/wrong-key must be rejected); check 10 fails if signing is
 * broken (neither repeated signature verifies). A harness that silently
 * passes everything cannot satisfy the reject-cases and the roundtrips
 * at once. Check 10 deliberately verifies both signatures instead of
 * comparing them byte-wise, so it holds for deterministic and
 * entropy-mixing (hedged) implementations alike.
 */

#include <stdio.h>
#include <string.h>

#include <lib25519.h>

#define CHECK(cond, name, fmt, args...) do {                        \
    int _ok = (cond) ? 1 : 0;                                       \
    ++total;                                                        \
    if (_ok) ++passed; else {                                       \
        ret = 1;                                                    \
        if (failed_list[0]) strcat(failed_list, " ");               \
        strcat(failed_list, name);                                  \
    }                                                               \
    printf("[%s] %s: " fmt "\n", _ok ? "PASS" : "FAIL", name, ##args); \
    fflush(stdout);                                                 \
} while (0)

int main(void)
{
    int ret = 0;
    int passed = 0;
    int total = 0;
    /* Names of failed checks for the summary line below, so even a
     * truncated log/summary still identifies the culprit. Worst case is
     * all 10 names (~190 chars); 320 bytes is ample. */
    static char failed_list[320] = "";
    /* Unbuffered so every [PASS]/[FAIL] reaches the ctest log even if a
     * later assertion aborts (read-only /tmp shells must not lose lines). */
    setvbuf(stdout, NULL, _IONBF, 0);

    /* 1. Public constants have the documented values. */
    CHECK(lib25519_dh_SECRETKEYBYTES == 32
          && lib25519_dh_PUBLICKEYBYTES == 32
          && lib25519_dh_BYTES == 32
          && lib25519_sign_SECRETKEYBYTES == 64
          && lib25519_sign_PUBLICKEYBYTES == 32
          && lib25519_sign_BYTES == 64,
          "const-sizes", "dh 32/32/32 sign 64/32/64");

    /* 2. X25519 key generation is randomized: two keypairs differ. */
    unsigned char xpk1[32], xsk1[32], xpk2[32], xsk2[32];
    lib25519_dh_keypair(xpk1, xsk1);
    lib25519_dh_keypair(xpk2, xsk2);
    CHECK(memcmp(xpk1, xpk2, 32) != 0 && memcmp(xsk1, xsk2, 32) != 0,
          "dh-keypair-random", "two fresh keypairs differ");

    /* 3. X25519 agreement: both sides derive the same shared secret. */
    unsigned char ka[32], kb[32];
    lib25519_dh(ka, xpk2, xsk1);
    lib25519_dh(kb, xpk1, xsk2);
    CHECK(memcmp(ka, kb, 32) == 0, "dh-agree", "shared secrets match");

    /* 4. The shared secret is not a trivial copy of a public key. */
    CHECK(memcmp(ka, xpk1, 32) != 0 && memcmp(ka, xpk2, 32) != 0,
          "dh-nontrivial", "secret differs from both public keys");

    /* 5. Ed25519 key generation is randomized as well. */
    unsigned char epk1[32], esk1[64], epk2[32], esk2[64];
    lib25519_sign_keypair(epk1, esk1);
    lib25519_sign_keypair(epk2, esk2);
    CHECK(memcmp(epk1, epk2, 32) != 0 && memcmp(esk1, esk2, 64) != 0,
          "sign-keypair-random", "two fresh ed25519 keypairs differ");

    /* 6. Sign/open roundtrip recovers the message. */
    static const unsigned char msg[] = "harmonyos lib25519 consumer test";
    long long mlen = (long long)(sizeof msg - 1);
    unsigned char sm[128];
    unsigned char mout[128];
    long long smlen = 0, moutlen = 0;
    lib25519_sign(sm, &smlen, msg, mlen, esk1);
    int rc = lib25519_sign_open(mout, &moutlen, sm, smlen, epk1);
    CHECK(rc == 0 && moutlen == mlen && memcmp(mout, msg, (size_t)mlen) == 0,
          "sign-roundtrip", "open rc=%d len=%lld", rc, moutlen);

    /* 7. A tampered signed message must be rejected. */
    sm[10] ^= 0x01;
    rc = lib25519_sign_open(mout, &moutlen, sm, smlen, epk1);
    sm[10] ^= 0x01;
    CHECK(rc != 0, "sign-tamper-reject", "tampered open rc=%d (want nonzero)", rc);

    /* 8. A wrong public key must be rejected. */
    rc = lib25519_sign_open(mout, &moutlen, sm, smlen, epk2);
    CHECK(rc != 0, "sign-wrongkey-reject", "wrong-key open rc=%d (want nonzero)", rc);

    /* 9. Empty message roundtrip. */
    lib25519_sign(sm, &smlen, msg, 0, esk1);
    rc = lib25519_sign_open(mout, &moutlen, sm, smlen, epk1);
    CHECK(rc == 0 && moutlen == 0, "sign-empty", "empty open rc=%d len=%lld", rc, moutlen);

    /* 10. Repeatability: signing the same message twice yields two signed
     * messages that each verify independently (no byte-equality check:
     * determinism is not an API guarantee — see file header). */
    unsigned char sm2[128];
    unsigned char mout2[128];
    long long smlen2 = 0, moutlen2 = 0;
    lib25519_sign(sm2, &smlen2, msg, mlen, esk1);
    lib25519_sign(sm, &smlen, msg, mlen, esk1);
    int rc2 = lib25519_sign_open(mout2, &moutlen2, sm2, smlen2, epk1);
    rc = lib25519_sign_open(mout, &moutlen, sm, smlen, epk1);
    CHECK(rc2 == 0 && moutlen2 == mlen && memcmp(mout2, msg, (size_t)mlen) == 0
          && rc == 0 && moutlen == mlen && memcmp(mout, msg, (size_t)mlen) == 0,
          "sign-resign-reverify", "both signatures verify rc=%d/%d", rc2, rc);

    printf("LIB25519_TEST_RESULT passed=%d total=%d\n", passed, total);
    printf("LIB25519_FAILED %s\n", failed_list[0] ? failed_list : "(none)");
    printf("test lib25519 API: %s\n", ret ? "FAIL" : "OK");
    return ret;
}
