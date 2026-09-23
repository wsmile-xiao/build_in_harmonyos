/*
 * Consumer-side API test for tiny-aes 1.0.0 (tiny-AES-c).
 *
 * The consumer links the packaged library and drives the public API declared by
 * the packaged aes.h. Every check has a failure path that makes main() return
 * non-zero, so a partially working package cannot pass.
 *
 * Assertion groups:
 *   1. HarmonyOS target verification (__OHOS__): a host-only consumer result
 *      must not be presentable as HarmonyOS validation.
 *   2. Packaged header configuration: the defaults baked into the installed
 *      aes.h (AES128, CBC/ECB/CTR all enabled) and the struct sizes they imply.
 *   3. Published AES known-answer vectors, taken from FIPS-197 (App. B and
 *      App. C.1) and NIST SP 800-38A (F.1.1, F.2.2 and F.5.1), recomputed
 *      independently with OpenSSL 3.6.4 before being frozen here.
 *   4. Round-trip correctness for ECB, CBC and CTR over multiple blocks.
 *   5. Mode semantics: CBC must actually chain (identical blocks must not
 *      produce identical ciphertext as under ECB), CTR must be symmetric in
 *      encrypt/decrypt direction, and both IV entry points must agree.
 *   6. Determinism and IV sensitivity (the IV check encrypts the same plaintext
 *      under two different IVs, so an IV-ignoring implementation fails it).
 *
 * Build-time note: aes.h defaults are used on purpose (no -D overrides), which
 * is exactly how a downstream consumer includes the packaged header. That
 * guarantees the struct layout used here matches the one the library was
 * compiled with.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "aes.h"

static int failures = 0;

static void check(int condition, const char *caption) {
    if (condition) {
        printf("ok - %s\n", caption);
    } else {
        printf("FAILED - %s\n", caption);
        failures++;
    }
}

static void check_hex(const char *caption, const uint8_t *actual,
                      const uint8_t *expected, size_t len) {
    if (memcmp(actual, expected, len) == 0) {
        printf("ok - %s\n", caption);
    } else {
        size_t i;
        printf("FAILED - %s\n  got      ", caption);
        for (i = 0; i < len; ++i) {
            printf("%02x", actual[i]);
        }
        printf("\n  expected ");
        for (i = 0; i < len; ++i) {
            printf("%02x", expected[i]);
        }
        printf("\n");
        failures++;
    }
}

/* FIPS-197 Appendix B / NIST SP 800-38A F.1.1 key (also used for CBC and CTR
 * below, where it is the SP 800-38A example key). */
static const uint8_t VEC_KEY[16] = {
    0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
    0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c};
/* FIPS-197 Appendix C.1 key. It is deliberately different from VEC_KEY: using
 * the wrong key here is exactly the mistake this pairing guards against. */
static const uint8_t FIPS197_KEY[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};
/* NIST SP 800-38A F.2.1 IV / F.5.1 initial counter block. */
static const uint8_t VEC_IV[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};
static const uint8_t VEC_CTR_IV[16] = {
    0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7,
    0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff};
/* FIPS-197 C.1 plaintext (single block). */
static const uint8_t FIPS197_PT[16] = {
    0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};
static const uint8_t FIPS197_CT[16] = {
    0x69, 0xc4, 0xe0, 0xd8, 0x6a, 0x7b, 0x04, 0x30,
    0xd8, 0xcd, 0xb7, 0x80, 0x70, 0xb4, 0xc5, 0x5a};
/* SP 800-38A F.1.1/F.2.1/F.2.2: first two plaintext blocks, the ECB ciphertext
 * of the first block, and the CBC ciphertext of both chained blocks. */
static const uint8_t SP38A_PT[32] = {
    0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
    0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a,
    0xae, 0x2d, 0x8a, 0x57, 0x1e, 0x03, 0xac, 0x9c,
    0x9e, 0xb7, 0x6f, 0xac, 0x45, 0xaf, 0x8e, 0x51};
static const uint8_t SP38A_ECB_CT[16] = {
    0x3a, 0xd7, 0x7b, 0xb4, 0x0d, 0x7a, 0x36, 0x60,
    0xa8, 0x9e, 0xca, 0xf3, 0x24, 0x66, 0xef, 0x97};
static const uint8_t SP38A_CBC_CT[32] = {
    0x76, 0x49, 0xab, 0xac, 0x81, 0x19, 0xb2, 0x46,
    0xce, 0xe9, 0x8e, 0x9b, 0x12, 0xe9, 0x19, 0x7d,
    0x50, 0x86, 0xcb, 0x9b, 0x50, 0x72, 0x19, 0xee,
    0x95, 0xdb, 0x11, 0x3a, 0x91, 0x76, 0x78, 0xb2};
/* SP 800-38A F.5.1 CTR-AES128 encryption of the same two plaintext blocks. */
static const uint8_t SP38A_CTR_CT[32] = {
    0x87, 0x4d, 0x61, 0x91, 0xb6, 0x20, 0xe3, 0x26,
    0x1b, 0xef, 0x68, 0x64, 0x99, 0x0d, 0xb6, 0xce,
    0x98, 0x06, 0xf6, 0x6b, 0x79, 0x70, 0xfd, 0xff,
    0x86, 0x17, 0x18, 0x7b, 0xb9, 0xff, 0xfd, 0xff};

int main(void) {
    struct AES_ctx ctx;
    uint8_t buf[32];
    uint8_t first[16];
    uint8_t second[16];
    uint8_t rerun[32];
    uint8_t iv_alt[32];
    uint8_t iv_b[16];

    /* 1. this executable must have been built for the OHOS target */
#if defined(__OHOS__)
    check(1, "HarmonyOS native consumer target (__OHOS__)");
#else
    check(0, "HarmonyOS native consumer target (__OHOS__)");
#endif

    /* 2. packaged header configuration: upstream defaults are baked into
     * aes.h, and the library was compiled with them, so the consumer must see
     * the same values. */
    check(AES_BLOCKLEN == 16, "AES_BLOCKLEN == 16 in packaged aes.h");
    check(AES_KEYLEN == 16 && AES_keyExpSize == 176,
          "AES128 default key schedule size in packaged aes.h");
    check(CBC == 1 && ECB == 1 && CTR == 1,
          "CBC, ECB and CTR all enabled in packaged aes.h");
    check(sizeof(struct AES_ctx) == 192,
          "struct AES_ctx layout (176-byte round keys + 16-byte IV)");

    /* 3a. FIPS-197 C.1 AES-128 ECB known answer (key 000102..0f) */
    memcpy(buf, FIPS197_PT, 16);
    AES_init_ctx(&ctx, FIPS197_KEY);
    AES_ECB_encrypt(&ctx, buf);
    check_hex("FIPS-197 C.1 AES-128 ECB encrypt", buf, FIPS197_CT, 16);

    /* 3b. FIPS-197 C.1 decryption of that ciphertext */
    memcpy(buf, FIPS197_CT, 16);
    AES_ECB_decrypt(&ctx, buf);
    check_hex("FIPS-197 C.1 AES-128 ECB decrypt", buf, FIPS197_PT, 16);

    /* 3c. NIST SP 800-38A F.1.1 AES-128 ECB (key 2b7e..3c), the same vector the
     * upstream test.c harness asserts, so the packaged library is checked
     * against the vector upstream considers authoritative. */
    memcpy(buf, SP38A_PT, 16);
    AES_init_ctx(&ctx, VEC_KEY);
    AES_ECB_encrypt(&ctx, buf);
    check_hex("NIST SP 800-38A F.1.1 AES-128 ECB encrypt", buf, SP38A_ECB_CT, 16);

    /* 3d. and its decryption */
    AES_ECB_decrypt(&ctx, buf);
    check_hex("NIST SP 800-38A F.1.1 AES-128 ECB decrypt", buf, SP38A_PT, 16);

    /* 3c. NIST SP 800-38A F.2.2 CBC-AES128, two chained blocks */
    memcpy(buf, SP38A_PT, 32);
    AES_init_ctx_iv(&ctx, VEC_KEY, VEC_IV);
    AES_CBC_encrypt_buffer(&ctx, buf, 32);
    check_hex("NIST SP 800-38A F.2.2 CBC-AES128 encrypt", buf, SP38A_CBC_CT, 32);

    /* 3d. CBC decryption returns the plaintext */
    AES_init_ctx_iv(&ctx, VEC_KEY, VEC_IV);
    AES_CBC_decrypt_buffer(&ctx, buf, 32);
    check_hex("NIST SP 800-38A F.2.2 CBC-AES128 decrypt", buf, SP38A_PT, 32);

    /* 3e. NIST SP 800-38A F.5.1 CTR-AES128 */
    memcpy(buf, SP38A_PT, 32);
    AES_init_ctx_iv(&ctx, VEC_KEY, VEC_CTR_IV);
    AES_CTR_xcrypt_buffer(&ctx, buf, 32);
    check_hex("NIST SP 800-38A F.5.1 CTR-AES128 xcrypt", buf, SP38A_CTR_CT, 32);

    /* 3f. CTR is its own inverse */
    AES_init_ctx_iv(&ctx, VEC_KEY, VEC_CTR_IV);
    AES_CTR_xcrypt_buffer(&ctx, buf, 32);
    check_hex("CTR-AES128 xcrypt is an involution", buf, SP38A_PT, 32);

    /* 4. CBC chaining: two identical blocks must not encrypt to identical
     * ciphertext (which is what ECB does). A CBC implementation that ignored
     * the IV would produce equal halves here. */
    memset(buf, 0x5a, 32);
    AES_init_ctx_iv(&ctx, VEC_KEY, VEC_IV);
    AES_CBC_encrypt_buffer(&ctx, buf, 32);
    memcpy(first, buf, 16);
    memcpy(second, buf + 16, 16);
    check(memcmp(first, second, 16) != 0, "CBC-AES128 chains identical blocks");

    /* 5. AES_ctx_set_iv must behave exactly like AES_init_ctx_iv */
    memcpy(buf, SP38A_PT, 32);
    AES_init_ctx(&ctx, VEC_KEY);
    AES_ctx_set_iv(&ctx, VEC_IV);
    AES_CBC_encrypt_buffer(&ctx, buf, 32);
    check_hex("AES_ctx_set_iv equals AES_init_ctx_iv", buf, SP38A_CBC_CT, 32);

    /* 6. determinism: same key, IV and input give the same output twice */
    memcpy(buf, SP38A_PT, 32);
    AES_init_ctx_iv(&ctx, VEC_KEY, VEC_IV);
    AES_CBC_encrypt_buffer(&ctx, buf, 32);
    memcpy(rerun, SP38A_PT, 32);
    AES_init_ctx_iv(&ctx, VEC_KEY, VEC_IV);
    AES_CBC_encrypt_buffer(&ctx, rerun, 32);
    check(memcmp(buf, rerun, 32) == 0, "CBC-AES128 is deterministic");

    /* 7. IV sensitivity: the *same* plaintext under a different IV must give a
     * different ciphertext. Comparing two encryptions of the same plaintext is
     * what makes this able to fail for an implementation that ignores the IV —
     * comparing different plaintexts would pass either way. */
    memcpy(iv_b, VEC_IV, 16);
    iv_b[0] ^= 0x01;
    memcpy(iv_alt, SP38A_PT, 32);
    AES_init_ctx_iv(&ctx, VEC_KEY, iv_b);
    AES_CBC_encrypt_buffer(&ctx, iv_alt, 32);
    check(memcmp(buf, iv_alt, 32) != 0, "CBC-AES128 output depends on the IV");

    if (failures != 0) {
        printf("FAILED: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("all assertions passed\n");
    return 0;
}
