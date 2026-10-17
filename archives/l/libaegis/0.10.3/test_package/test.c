/* libaegis/0.10.3 consumer test.
 *
 * Covers: aegis_init runtime CPU dispatch, one-shot and detached API round
 * trips for all six variants, authentication-failure negatives, boundary
 * lengths (0/1/RATE/RATE+1), embedded deterministic KAT vectors from the
 * upstream rooterberg sets, and repeatability of outputs.
 */

#include <stdio.h>
#include <string.h>

#include "aegis.h"
#include "aegis128l.h"
#include "aegis128x2.h"
#include "aegis128x4.h"
#include "aegis256.h"
#include "aegis256x2.h"
#include "aegis256x4.h"

#include "kat_vectors.h"

static int checks = 0;
static int failures = 0;

#define CHECK(cond, name)                                              \
    do {                                                               \
        checks++;                                                      \
        if (cond) {                                                    \
            printf("ok %2d - %s\n", checks, name);                     \
        } else {                                                       \
            failures++;                                                \
            printf("FAIL %2d - %s\n", checks, name);                   \
        }                                                              \
    } while (0)

/* ------------------------------------------------------------------ */
/* Deterministic KAT from upstream rooterberg vectors                  */
/* ------------------------------------------------------------------ */

static void
run_kat(const kat_vector_t *v, size_t n, const char *set, int is_aegis256)
{
    uint8_t msg[KAT_MAX_DATA];

    for (size_t i = 0; i < n; i++) {
        const kat_vector_t *t = &v[i];
        int rc;
        if (is_aegis256) {
            rc = aegis256_decrypt_detached(msg, t->ct, t->ct_len, t->tag, t->tag_len,
                                           t->aad, t->aad_len, t->nonce, t->key);
        } else {
            rc = aegis128l_decrypt_detached(msg, t->ct, t->ct_len, t->tag, t->tag_len,
                                            t->aad, t->aad_len, t->nonce, t->key);
        }
        if (t->expect_valid) {
            CHECK(rc == 0 && memcmp(msg, t->msg, t->msg_len) == 0, t->name);
        } else {
            CHECK(rc == -1, t->name);
        }
    }
    (void) set;
}

/* ------------------------------------------------------------------ */
/* Round trip + negatives + boundary lengths                           */
/* ------------------------------------------------------------------ */

static void
fill_pattern(uint8_t *p, size_t n, uint8_t seed)
{
    for (size_t i = 0; i < n; i++) {
        p[i] = (uint8_t)(seed + i);
    }
}

static int
roundtrip_128l(size_t mlen, size_t adlen, size_t maclen)
{
    uint8_t key[16], nonce[16], msg[300], ad[300];
    uint8_t ct[300 + 32], out[300];

    fill_pattern(key, sizeof key, 0x10);
    fill_pattern(nonce, sizeof nonce, 0x20);
    fill_pattern(msg, mlen, 0x30);
    fill_pattern(ad, adlen, 0x40);

    /* one-shot: tag is appended at c[mlen] */
    if (aegis128l_encrypt(ct, maclen, msg, mlen, ad, adlen, nonce, key) != 0) {
        return 0;
    }
    if (mlen > 1 && memcmp(ct, msg, mlen) == 0) {
        return 0; /* ciphertext must differ from plaintext */
    }
    /* one-shot decrypt: clen is ciphertext+tag; tag sits at c[clen-maclen] */
    if (aegis128l_decrypt(out, ct, mlen + maclen, maclen, ad, adlen, nonce, key) != 0) {
        return 0;
    }
    return memcmp(out, msg, mlen) == 0;
}

static int
roundtrip_256(size_t mlen, size_t adlen, size_t maclen)
{
    uint8_t key[32], nonce[32], msg[300], ad[300];
    uint8_t ct[300 + 32], out[300];

    fill_pattern(key, sizeof key, 0x10);
    fill_pattern(nonce, sizeof nonce, 0x20);
    fill_pattern(msg, mlen, 0x30);
    fill_pattern(ad, adlen, 0x40);

    if (aegis256_encrypt(ct, maclen, msg, mlen, ad, adlen, nonce, key) != 0) {
        return 0;
    }
    if (mlen > 1 && memcmp(ct, msg, mlen) == 0) {
        return 0;
    }
    /* one-shot decrypt: clen is ciphertext+tag; tag sits at c[clen-maclen] */
    if (aegis256_decrypt(out, ct, mlen + maclen, maclen, ad, adlen, nonce, key) != 0) {
        return 0;
    }
    return memcmp(out, msg, mlen) == 0;
}

static int
roundtrip_x(size_t mlen, size_t adlen)
{
    uint8_t key16[16], key32[32], nonce16[16], nonce32[32];
    uint8_t msg[300], ad[300], ct[300 + 32], out[300];

    fill_pattern(key16, sizeof key16, 0x10);
    fill_pattern(key32, sizeof key32, 0x11);
    fill_pattern(nonce16, sizeof nonce16, 0x20);
    fill_pattern(nonce32, sizeof nonce32, 0x21);
    fill_pattern(msg, mlen, 0x30);
    fill_pattern(ad, adlen, 0x40);

    if (aegis128x2_encrypt(ct, 16, msg, mlen, ad, adlen, nonce16, key16) != 0 ||
        aegis128x2_decrypt(out, ct, mlen + 16, 16, ad, adlen, nonce16, key16) != 0 ||
        memcmp(out, msg, mlen) != 0) {
        return 0;
    }
    if (aegis128x4_encrypt(ct, 16, msg, mlen, ad, adlen, nonce16, key16) != 0 ||
        aegis128x4_decrypt(out, ct, mlen + 16, 16, ad, adlen, nonce16, key16) != 0 ||
        memcmp(out, msg, mlen) != 0) {
        return 0;
    }
    if (aegis256x2_encrypt(ct, 16, msg, mlen, ad, adlen, nonce32, key32) != 0 ||
        aegis256x2_decrypt(out, ct, mlen + 16, 16, ad, adlen, nonce32, key32) != 0 ||
        memcmp(out, msg, mlen) != 0) {
        return 0;
    }
    if (aegis256x4_encrypt(ct, 16, msg, mlen, ad, adlen, nonce32, key32) != 0 ||
        aegis256x4_decrypt(out, ct, mlen + 16, 16, ad, adlen, nonce32, key32) != 0 ||
        memcmp(out, msg, mlen) != 0) {
        return 0;
    }
    return 1;
}

static int
tampered_ct_rejected(void)
{
    uint8_t key[16], nonce[16], msg[64], ct[64 + 32], out[64];

    fill_pattern(key, sizeof key, 1);
    fill_pattern(nonce, sizeof nonce, 2);
    fill_pattern(msg, sizeof msg, 3);
    if (aegis128l_encrypt(ct, 16, msg, sizeof msg, NULL, 0, nonce, key) != 0) {
        return 0;
    }
    ct[0] ^= 0x01;
    return aegis128l_decrypt(out, ct, sizeof msg + 16, 16, NULL, 0, nonce, key) == -1;
}

static int
tampered_mac_rejected(void)
{
    uint8_t key[16], nonce[16], msg[64], ct[64 + 32], out[64];

    fill_pattern(key, sizeof key, 1);
    fill_pattern(nonce, sizeof nonce, 2);
    fill_pattern(msg, sizeof msg, 3);
    if (aegis128l_encrypt(ct, 16, msg, sizeof msg, NULL, 0, nonce, key) != 0) {
        return 0;
    }
    ct[sizeof msg] ^= 0x80; /* first MAC byte (tag appended at c[mlen]) */
    return aegis128l_decrypt(out, ct, sizeof msg + 16, 16, NULL, 0, nonce, key) == -1;
}

static int
wrong_key_rejected(void)
{
    uint8_t key[16], nonce[16], msg[64], ct[64 + 32], out[64];

    fill_pattern(key, sizeof key, 1);
    fill_pattern(nonce, sizeof nonce, 2);
    fill_pattern(msg, sizeof msg, 3);
    if (aegis128l_encrypt(ct, 16, msg, sizeof msg, NULL, 0, nonce, key) != 0) {
        return 0;
    }
    key[0] ^= 0xff;
    return aegis128l_decrypt(out, ct, sizeof msg + 16, 16, NULL, 0, nonce, key) == -1;
}

static int
deterministic_output(void)
{
    uint8_t key[16], nonce[16], msg[32];
    uint8_t ct1[32 + 32], ct2[32 + 32];

    fill_pattern(key, sizeof key, 7);
    fill_pattern(nonce, sizeof nonce, 8);
    fill_pattern(msg, sizeof msg, 9);
    if (aegis128l_encrypt(ct1, 16, msg, sizeof msg, NULL, 0, nonce, key) != 0 ||
        aegis128l_encrypt(ct2, 16, msg, sizeof msg, NULL, 0, nonce, key) != 0) {
        return 0;
    }
    return memcmp(ct1, ct2, sizeof msg + 16) == 0;
}

/* Incremental (state) API must produce the same ciphertext+tag as one-shot. */
static int
incremental_matches_oneshot(void)
{
    uint8_t key[16], nonce[16], msg[100];
    uint8_t ct1[100 + 16], ct2[100 + 16];

    fill_pattern(key, sizeof key, 0xa1);
    fill_pattern(nonce, sizeof nonce, 0xb2);
    fill_pattern(msg, sizeof msg, 0xc3);

    if (aegis128l_encrypt(ct1, 16, msg, sizeof msg, NULL, 0, nonce, key) != 0) {
        return 0;
    }

    aegis128l_state st;
    aegis128l_state_init(&st, NULL, 0, nonce, key);
    aegis128l_state_encrypt_update(&st, ct2, msg, 40);
    aegis128l_state_encrypt_update(&st, ct2 + 40, msg + 40, 60);
    if (aegis128l_state_encrypt_final(&st, ct2 + sizeof msg, 16) != 0) {
        return 0;
    }
    return memcmp(ct1, ct2, sizeof msg + 16) == 0;
}

int
main(void)
{
    CHECK(aegis_init() == 0, "aegis_init runtime CPU dispatch");

    /* --- KAT: 4 sets x 4 embedded vectors ---------------------------- */
    run_kat(kat_aegis128_l, sizeof kat_aegis128_l / sizeof kat_aegis128_l[0], "aegis128_l", 0);
    run_kat(kat_aegis128_l_256, sizeof kat_aegis128_l_256 / sizeof kat_aegis128_l_256[0], "aegis128_l_256", 0);
    run_kat(kat_aegis256, sizeof kat_aegis256 / sizeof kat_aegis256[0], "aegis256", 1);
    run_kat(kat_aegis256_256, sizeof kat_aegis256_256 / sizeof kat_aegis256_256[0], "aegis256_256", 1);

    /* --- round trips incl. boundary lengths -------------------------- */
    CHECK(roundtrip_128l(0, 0, 16), "aegis128l roundtrip mlen=0 adlen=0");
    CHECK(roundtrip_128l(1, 0, 16), "aegis128l roundtrip mlen=1");
    CHECK(roundtrip_128l(16, 0, 16), "aegis128l roundtrip mlen=16 (RATE)");
    CHECK(roundtrip_128l(17, 0, 16), "aegis128l roundtrip mlen=17 (RATE+1)");
    CHECK(roundtrip_128l(32, 16, 16), "aegis128l roundtrip mlen=32 adlen=16");
    CHECK(roundtrip_128l(100, 200, 16), "aegis128l roundtrip mlen=100 adlen=200");
    CHECK(roundtrip_128l(100, 200, 32), "aegis128l roundtrip maclen=32 (max tag)");
    CHECK(roundtrip_256(0, 0, 16), "aegis256 roundtrip mlen=0");
    CHECK(roundtrip_256(1, 0, 16), "aegis256 roundtrip mlen=1");
    CHECK(roundtrip_256(32, 0, 16), "aegis256 roundtrip mlen=32 (RATE)");
    CHECK(roundtrip_256(33, 0, 16), "aegis256 roundtrip mlen=33 (RATE+1)");
    CHECK(roundtrip_256(100, 200, 16), "aegis256 roundtrip mlen=100 adlen=200");
    CHECK(roundtrip_x(0, 0), "aegis128x2/128x4/256x2/256x4 roundtrip mlen=0");
    CHECK(roundtrip_x(1, 16), "x-variants roundtrip mlen=1");
    CHECK(roundtrip_x(33, 200), "x-variants roundtrip mlen=33 adlen=200");

    /* --- authentication failures ------------------------------------- */
    CHECK(tampered_ct_rejected(), "aegis128l tampered ciphertext rejected");
    CHECK(tampered_mac_rejected(), "aegis128l tampered MAC rejected");
    CHECK(wrong_key_rejected(), "aegis128l wrong key rejected");

    /* --- determinism -------------------------------------------------- */
    CHECK(deterministic_output(), "aegis128l deterministic output");
    CHECK(incremental_matches_oneshot(), "aegis128l incremental == one-shot");

    if (failures == 0) {
        printf("all %d checks passed\n", checks);
        return 0;
    }
    printf("%d/%d checks FAILED\n", failures, checks);
    return 1;
}
