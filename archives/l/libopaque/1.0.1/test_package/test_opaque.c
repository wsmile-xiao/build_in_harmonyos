/* Consumer test for libopaque 1.0.1 on HarmonyOS PC.
 *
 * Exercises the real public API from <opaque.h> end to end, mirroring the
 * upstream src/tests/opaque-test.c flow but with explicit per-step checks:
 * one-step registration, full credential AKE, shared-secret comparison,
 * explicit user authentication, export-key sanity, the 4-step private
 * registration variant, and a wrong-password mismatch (negative) check.
 *
 * Each check prints "PASS i/N name"; the final summary line
 * OPAQUE_CONSUMER_CHECKS_PASSED=x/y is parsed by test_package/conanfile.py
 * for the HMBS_TEST_PACKAGE_RESULT marker. Any failure returns nonzero.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <sodium.h>
#include <opaque.h>

#define TOTAL_CHECKS 10

static int ran = 0;
static int passed = 0;

static void check(int cond, const char *name)
{
    ++ran;
    if (cond) {
        ++passed;
        printf("PASS %d/%d %s\n", ran, TOTAL_CHECKS, name);
    } else {
        printf("FAIL %d/%d %s\n", ran, TOTAL_CHECKS, name);
    }
}

static int all_zero(const uint8_t *buf, size_t len)
{
    size_t i;
    for (i = 0; i < len; ++i) {
        if (buf[i] != 0) {
            return 0;
        }
    }
    return 1;
}

int main(void)
{
    static const uint8_t pwd[] = "correct horse battery staple";
    static const uint16_t pwd_len = (uint16_t)(sizeof pwd - 1);
    static const uint8_t ctx[] = "hmbs-consumer-test";
    Opaque_Ids ids = {4, (uint8_t *)"user", 6, (uint8_t *)"server"};
    uint8_t rec[OPAQUE_USER_RECORD_LEN];
    uint8_t export_key[crypto_hash_sha512_BYTES];
    uint8_t sec[OPAQUE_USER_SESSION_SECRET_LEN + sizeof pwd];
    uint8_t ke1[OPAQUE_USER_SESSION_PUBLIC_LEN];
    uint8_t ke2[OPAQUE_SERVER_SESSION_LEN];
    uint8_t sk[OPAQUE_SHARED_SECRETBYTES];
    uint8_t pk[OPAQUE_SHARED_SECRETBYTES];
    uint8_t auth_s[crypto_auth_hmacsha512_BYTES];
    uint8_t auth_u[crypto_auth_hmacsha512_BYTES];

    if (sodium_init() < 0) {
        printf("FAIL 0/%d sodium_init\n", TOTAL_CHECKS);
        return 1;
    }

    /* 1: one-step registration (server-side, paper variant). */
    check(opaque_Register(pwd, pwd_len, NULL, &ids, rec, export_key) == 0,
          "opaque_Register");

    /* 2-4: full credential AKE. */
    check(opaque_CreateCredentialRequest(pwd, pwd_len, sec, ke1) == 0,
          "opaque_CreateCredentialRequest");
    check(opaque_CreateCredentialResponse(ke1, rec, &ids, ctx, (uint16_t)(sizeof ctx),
                                          ke2, sk, auth_s) == 0,
          "opaque_CreateCredentialResponse");
    check(opaque_RecoverCredentials(ke2, sec, ctx, (uint16_t)(sizeof ctx), &ids,
                                    pk, auth_u, export_key) == 0,
          "opaque_RecoverCredentials");

    /* 5: client and server derived the same shared secret. */
    check(sodium_memcmp(sk, pk, sizeof sk) == 0, "shared-secret-match");

    /* 6: explicit client authentication. */
    check(opaque_UserAuth(auth_s, auth_u) == 0, "opaque_UserAuth");

    /* 7: export key is real key material, not zeros. */
    check(!all_zero(export_key, sizeof export_key), "export-key-nonzero");

    /* 8: 4-step private registration variant (password never leaves client). */
    {
        uint8_t req[crypto_core_ristretto255_BYTES];
        uint8_t rsec[OPAQUE_REGISTER_SECRET_LEN];
        uint8_t rpub[OPAQUE_REGISTER_PUBLIC_LEN];
        uint8_t rrec[OPAQUE_REGISTRATION_RECORD_LEN];
        uint8_t usec[OPAQUE_REGISTER_USER_SEC_LEN + sizeof pwd];
        uint8_t ek2[crypto_hash_sha512_BYTES];
        int ok = opaque_CreateRegistrationRequest(pwd, pwd_len, usec, req) == 0;
        ok = ok && opaque_CreateRegistrationResponse(req, NULL, rsec, rpub) == 0;
        ok = ok && opaque_FinalizeRequest(usec, rpub, &ids, rrec, ek2) == 0;
        opaque_StoreUserRecord(rsec, rrec, rec);
        check(ok, "private-registration-4-step");
    }

    /* 9: AKE against the privately-registered record agrees as well. */
    {
        int ok = opaque_CreateCredentialRequest(pwd, pwd_len, sec, ke1) == 0;
        ok = ok && opaque_CreateCredentialResponse(ke1, rec, &ids, ctx,
                                                   (uint16_t)(sizeof ctx),
                                                   ke2, sk, auth_s) == 0;
        ok = ok && opaque_RecoverCredentials(ke2, sec, ctx, (uint16_t)(sizeof ctx),
                                             &ids, pk, auth_u, export_key) == 0;
        ok = ok && sodium_memcmp(sk, pk, sizeof sk) == 0;
        ok = ok && opaque_UserAuth(auth_s, auth_u) == 0;
        check(ok, "ake-on-private-record");
    }

    /* 10 (negative): wrong password must NOT yield the server secret.
     * Either explicit rejection (nonzero return) or a mismatched secret
     * counts as pass; only agreement with the server secret would fail. */
    {
        static const uint8_t wrong[] = "wrong password";
        uint8_t bad_pk[OPAQUE_SHARED_SECRETBYTES];
        uint8_t bad_auth[crypto_auth_hmacsha512_BYTES];
        uint8_t bad_sec[OPAQUE_USER_SESSION_SECRET_LEN + sizeof wrong];
        uint8_t bad_ke1[OPAQUE_USER_SESSION_PUBLIC_LEN];
        int rc;
        int ok = opaque_CreateCredentialRequest(wrong, (uint16_t)(sizeof wrong - 1),
                                                bad_sec, bad_ke1) == 0;
        rc = opaque_RecoverCredentials(ke2, bad_sec, ctx,
                                       (uint16_t)(sizeof ctx), &ids,
                                       bad_pk, bad_auth, export_key);
        ok = ok && (rc != 0 || sodium_memcmp(sk, bad_pk, sizeof sk) != 0);
        check(ok, "wrong-password-mismatch");
    }

    printf("OPAQUE_CONSUMER_CHECKS_PASSED=%d/%d\n", passed, TOTAL_CHECKS);
    if (passed != TOTAL_CHECKS) {
        return 1;
    }
    puts("libopaque 1.0.1 consumer test passed");
    return 0;
}
