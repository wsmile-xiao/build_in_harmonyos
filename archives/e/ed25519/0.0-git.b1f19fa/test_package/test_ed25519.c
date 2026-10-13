#include <stdio.h>
#include <string.h>

#include "ed25519.h"

/*
 * Conan consumer test for ed25519/0.0-git.b1f19fa.
 *
 * Runs the official RFC 8032 section 7.1 Ed25519 test vectors
 * (TEST 1: empty message, TEST 2: one-byte message, TEST 3: two-byte
 * message) against the packaged library:
 *
 *   1. ed25519_create_keypair(seed) must derive the exact expected
 *      public key from the official 32-byte secret key (seed),
 *   2. ed25519_sign must produce the exact deterministic 64-byte
 *      signature from the RFC,
 *   3. ed25519_verify must accept the signature,
 *   4. flipping a bit in the signature's R half must make
 *      ed25519_verify reject it.
 *
 * 3 vectors x 4 assertions = 12 assertions in total.
 */

static int failures = 0;

static void check(int cond, const char *what) {
    if (cond) {
        printf("ok: %s\n", what);
    } else {
        ++failures;
        printf("FAILED: %s\n", what);
    }
}

static void hex_decode(const char *hex, unsigned char *out, size_t len) {
    size_t i;
    for (i = 0; i < len; ++i) {
        unsigned int byte = 0;
        sscanf(hex + 2 * i, "%2x", &byte);
        out[i] = (unsigned char)byte;
    }
}

struct rfc8032_case {
    const char *name;
    const char *secret_key_hex; /* 32-byte seed  */
    const char *public_key_hex; /* 32-byte A     */
    const char *message_hex;    /* message bytes */
    const char *signature_hex;  /* 64-byte R||s  */
};

static const struct rfc8032_case CASES[] = {
    /* RFC 8032 section 7.1 TEST 1 (empty message) */
    {
        "RFC 8032 7.1 TEST 1",
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
    },
    /* RFC 8032 section 7.1 TEST 2 (message 0x72) */
    {
        "RFC 8032 7.1 TEST 2",
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    },
    /* RFC 8032 section 7.1 TEST 3 (message 0xaf82) */
    {
        "RFC 8032 7.1 TEST 3",
        "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
        "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
        "af82",
        "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a",
    },
};

int main(void) {
    unsigned char seed[32];
    unsigned char public_key[32], private_key[64];
    unsigned char expected_public[32], expected_signature[64];
    unsigned char signature[64], message[1024];
    size_t c;
    int total = 0;

    for (c = 0; c < sizeof(CASES) / sizeof(CASES[0]); ++c) {
        const struct rfc8032_case *tc = &CASES[c];
        size_t msg_len = strlen(tc->message_hex) / 2;

        hex_decode(tc->secret_key_hex, seed, 32);
        hex_decode(tc->public_key_hex, expected_public, 32);
        hex_decode(tc->signature_hex, expected_signature, 64);
        hex_decode(tc->message_hex, message, msg_len);

        ed25519_create_keypair(public_key, private_key, seed);
        check(memcmp(public_key, expected_public, 32) == 0,
              "keypair derives the RFC 8032 public key");

        ed25519_sign(signature, message, msg_len, public_key, private_key);
        check(memcmp(signature, expected_signature, 64) == 0,
              "sign produces the deterministic RFC 8032 signature");

        check(ed25519_verify(signature, message, msg_len, public_key) == 1,
              "verify accepts the RFC 8032 signature");

        signature[0] ^= 0x01;
        check(ed25519_verify(signature, message, msg_len, public_key) == 0,
              "verify rejects a tampered signature");

        total += 4;
    }

    if (failures != 0) {
        fprintf(stderr, "ed25519 consumer test failed: %d assertion(s) failed\n",
                failures);
        return 1;
    }
    printf("ed25519 consumer test passed: %d assertions\n", total);
    return 0;
}
