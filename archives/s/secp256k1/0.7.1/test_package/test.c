#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <secp256k1.h>
#include <secp256k1_ecdh.h>
#include <secp256k1_extrakeys.h>
#include <secp256k1_schnorrsig.h>

int main(void) {
    /* ── Context ── */
    secp256k1_context *ctx = secp256k1_context_create(
        SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);
    if (!ctx) {
        printf("Error: secp256k1_context_create failed\n");
        return 1;
    }

    /* ── Secret key ── */
    unsigned char seckey[32];
    memset(seckey, 0x11, 32);
    seckey[0] &= 0x7f; /* ensure scalar < 2^255, thus valid range */

    if (!secp256k1_ec_seckey_verify(ctx, seckey)) {
        printf("Error: secp256k1_ec_seckey_verify failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }

    /* ── Pubkey creation (v0.7.1 3-arg API) ── */
    secp256k1_pubkey pubkey;
    if (!secp256k1_ec_pubkey_create(ctx, &pubkey, seckey)) {
        printf("Error: secp256k1_ec_pubkey_create failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }

    /* ── Serialize pubkey (compressed) ── */
    unsigned char serialized[33];
    size_t serialized_len = sizeof(serialized);
    if (!secp256k1_ec_pubkey_serialize(ctx, serialized, &serialized_len,
                                       &pubkey, SECP256K1_EC_COMPRESSED)) {
        printf("Error: secp256k1_ec_pubkey_serialize failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }
    printf("Pubkey (compressed, %zu bytes): ", serialized_len);
    for (size_t i = 0; i < serialized_len; i++) {
        printf("%02x", serialized[i]);
    }
    printf("\n");

    /* ── ECDH module test ── */
    unsigned char seckey2[32];
    memset(seckey2, 0x22, 32);
    seckey2[0] &= 0x7f; /* ensure scalar < 2^255, thus valid range */
    secp256k1_pubkey pubkey2;
    if (!secp256k1_ec_pubkey_create(ctx, &pubkey2, seckey2)) {
        printf("Error: second pubkey creation failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }

    unsigned char shared_secret[32];
    if (!secp256k1_ecdh(ctx, shared_secret, &pubkey2, seckey, NULL, NULL)) {
        printf("Error: secp256k1_ecdh failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }
    printf("ECDH shared secret: ");
    for (int i = 0; i < 32; i++) {
        printf("%02x", shared_secret[i]);
    }
    printf("\n");

    /* ── Extrakeys + Schnorr module test ── */
    secp256k1_keypair keypair;
    if (!secp256k1_keypair_create(ctx, &keypair, seckey)) {
        printf("Error: secp256k1_keypair_create failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }

    secp256k1_xonly_pubkey xonly_pub;
    if (!secp256k1_keypair_xonly_pub(ctx, &xonly_pub, NULL, &keypair)) {
        printf("Error: secp256k1_keypair_xonly_pub failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }

    unsigned char msg32[32];
    memset(msg32, 0xAB, 32);

    unsigned char aux_rand[32];
    memset(aux_rand, 0xCD, 32);

    unsigned char schnorr_sig[64];
    if (!secp256k1_schnorrsig_sign32(ctx, schnorr_sig, msg32, &keypair,
                                     aux_rand)) {
        printf("Error: secp256k1_schnorrsig_sign32 failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }

    if (!secp256k1_schnorrsig_verify(ctx, schnorr_sig, msg32, 32, &xonly_pub)) {
        printf("Error: secp256k1_schnorrsig_verify failed\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }
    printf("Schnorr signature verified successfully\n");

    /* ── Tamper test: flip a bit, verify should fail ── */
    unsigned char bad_sig[64];
    memcpy(bad_sig, schnorr_sig, 64);
    bad_sig[0] ^= 0x01;
    if (secp256k1_schnorrsig_verify(ctx, bad_sig, msg32, 32, &xonly_pub)) {
        printf("Error: Schnorr verify should have failed on tampered sig\n");
        secp256k1_context_destroy(ctx);
        return 1;
    }
    printf("Schnorr tamper test passed (correctly rejected)\n");

    secp256k1_context_destroy(ctx);
    printf("secp256k1 test: OK\n");
    return 0;
}
