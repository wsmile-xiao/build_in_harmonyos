/*
 * test_hydrogen.c — libhydrogen 0.0-git.264bf42 consumer test (R34).
 *
 * Exercises the packaged library from a consumer's perspective:
 *   1. hydro_init
 *   2. hydro_sign_keypair keygen + hydro_sign_create / hydro_sign_verify
 *      roundtrip (primary scenario) + tamper rejection
 *   3. deterministic keygen reproducibility
 *   4. incremental signing state API (init/update/final create+verify)
 *   5. hydro_secretbox encrypt/decrypt roundtrip + tamper rejection
 *   6. hydro_hash keyed hash reproducibility
 *   7. hydro_kdf subkey derivation reproducibility
 *
 * Exits non-zero on any failure (explicit CHECK macro, effective under -DNDEBUG).
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "hydrogen.h"

/* Release(-DNDEBUG) 下 assert 被剔除——改显式 CHECK 宏保证测试恒有效（AI review P2 整改） */
#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "CHECK failed: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

static const char *sign_ctx = "libtest";

int main(void)
{
    hydro_sign_keypair kp;
    hydro_sign_keypair kp2;
    hydro_sign_keypair kp_seed_a;
    hydro_sign_keypair kp_seed_b;
    uint8_t            seed[hydro_sign_SEEDBYTES];
    uint8_t            sig[hydro_sign_BYTES];
    uint8_t            sig2[hydro_sign_BYTES];
    uint8_t            tampered[hydro_sign_BYTES];
    hydro_sign_state   st_a;
    hydro_sign_state   st_b;
    uint8_t            secretbox_key[hydro_secretbox_KEYBYTES];
    uint8_t            secretbox_key2[hydro_secretbox_KEYBYTES];
    uint8_t            cipher[hydro_secretbox_HEADERBYTES + 64];
    uint8_t            plain[64];
    uint8_t            plain2[64];
    uint8_t            hash_key[hydro_hash_KEYBYTES];
    uint8_t            hash_a[32];
    uint8_t            hash_b[32];
    uint8_t            kdf_key[hydro_kdf_KEYBYTES];
    uint8_t            subkey_a[32];
    uint8_t            subkey_b[32];
    const char        *message = "HarmonyOS libhydrogen consumer roundtrip";
    int                rc;
    size_t             clen;
    size_t             i;

    /* 1. Initialization must succeed. */
    rc = hydro_init();
    CHECK(rc == 0);

    /* 2. Keypair generation + sign/verify roundtrip (primary scenario). */
    hydro_sign_keygen(&kp);
    CHECK(hydro_sign_create(sig, message, strlen(message), sign_ctx, kp.sk) == 0);
    rc = hydro_sign_verify(sig, message, strlen(message), sign_ctx, kp.pk);
    CHECK(rc == 0);

    /* Wrong message must fail verification. */
    rc = hydro_sign_verify(sig, "other message", 13, sign_ctx, kp.pk) /* len=13 == strlen 恒等（AI review P3 整改：原 14 多计 1） */;
    CHECK(rc == -1);

    /* Wrong public key must fail verification. */
    hydro_sign_keygen(&kp2);
    rc = hydro_sign_verify(sig, message, strlen(message), sign_ctx, kp2.pk);
    CHECK(rc == -1);

    /* Tampered signature must fail verification. */
    memcpy(tampered, sig, sizeof tampered);
    tampered[0] ^= 0x01;
    rc = hydro_sign_verify(tampered, message, strlen(message), sign_ctx, kp.pk);
    CHECK(rc != 0);

    /* 3. Deterministic keygen: same seed -> identical keypair. */
    hydro_secretbox_keygen(seed); /* any 32-byte seed source */
    hydro_sign_keygen_deterministic(&kp_seed_a, seed);
    hydro_sign_keygen_deterministic(&kp_seed_b, seed);
    CHECK(memcmp(kp_seed_a.pk, kp_seed_b.pk, hydro_sign_PUBLICKEYBYTES) == 0);
    CHECK(memcmp(kp_seed_a.sk, kp_seed_b.sk, hydro_sign_SECRETKEYBYTES) == 0);

    /* 4. Incremental signing state API: two updates vs same stream. */
    CHECK(hydro_sign_init(&st_a, sign_ctx) == 0);
    CHECK(hydro_sign_update(&st_a, message, 10) == 0);
    CHECK(hydro_sign_update(&st_a, message + 10, strlen(message) - 10) == 0);
    CHECK(hydro_sign_final_create(&st_a, sig2, kp.sk) == 0);
    rc = hydro_sign_verify(sig2, message, strlen(message), sign_ctx, kp.pk);
    CHECK(rc == 0);

    CHECK(hydro_sign_init(&st_b, sign_ctx) == 0);
    CHECK(hydro_sign_update(&st_b, message, strlen(message)) == 0);
    CHECK(hydro_sign_final_verify(&st_b, sig2, kp.pk) == 0);

    /* 5. secretbox encrypt/decrypt roundtrip + tamper rejection. */
    hydro_secretbox_keygen(secretbox_key);
    hydro_secretbox_keygen(secretbox_key2);
    for (i = 0; i < sizeof plain; i++) {
        plain[i] = (uint8_t) (i * 7 + 1);
    }
    /* libhydrogen 语义：encrypt 返回 0=成功/-1=失败（非密文长度——那是 libsodium
     * crypto_secretbox_easy 的语义）。密文长度恒为 mlen+HEADERBYTES，显式计算。 */
    CHECK(hydro_secretbox_encrypt(cipher, plain, sizeof plain, 42, sign_ctx,
                                  secretbox_key) == 0);
    clen = sizeof plain + hydro_secretbox_HEADERBYTES;
    CHECK(hydro_secretbox_decrypt(plain2, cipher, clen, 42, sign_ctx,
                                   secretbox_key) == 0);
    CHECK(memcmp(plain, plain2, sizeof plain) == 0);

    /* Wrong key must fail. */
    rc = hydro_secretbox_decrypt(plain2, cipher, clen, 42, sign_ctx,
                                 secretbox_key2);
    CHECK(rc == -1);

    /* Tampered ciphertext must fail. */
    cipher[hydro_secretbox_HEADERBYTES] ^= 0x01;
    rc = hydro_secretbox_decrypt(plain2, cipher, clen, 42, sign_ctx,
                                 secretbox_key);
    CHECK(rc == -1);

    /* 6. Keyed hash reproducibility. */
    hydro_hash_keygen(hash_key);
    CHECK(hydro_hash_hash(hash_a, sizeof hash_a, message, strlen(message),
                           sign_ctx, hash_key) == 0);
    CHECK(hydro_hash_hash(hash_b, sizeof hash_b, message, strlen(message),
                           sign_ctx, hash_key) == 0);
    CHECK(memcmp(hash_a, hash_b, sizeof hash_a) == 0);

    /* 7. KDF subkey derivation reproducibility. */
    hydro_kdf_keygen(kdf_key);
    CHECK(hydro_kdf_derive_from_key(subkey_a, sizeof subkey_a, 7, sign_ctx,
                                     kdf_key) == 0);
    CHECK(hydro_kdf_derive_from_key(subkey_b, sizeof subkey_b, 7, sign_ctx,
                                     kdf_key) == 0);
    CHECK(memcmp(subkey_a, subkey_b, sizeof subkey_a) == 0);

    printf("PASS: libhydrogen consumer tests "
           "(init/sign keypair roundtrip/tamper/deterministic keygen/"
           "incremental sign/secretbox/hash/kdf) OK\n");
    return 0;
}
