/* test_libcaes.c — consumer test for libcaes/0-20251121.
 *
 * 1 complete end-to-end consumer use case containing 9 checks against
 * the public API (no stubs):
 *  1. libcaes_get_version() returns non-empty string
 *  2. libcaes_context_initialize() == 1
 *  3. libcaes_context_set_key() AES-128 ENCRYPT == 1
 *  4. libcaes_crypt_ecb() ENCRYPT one block == 1
 *  5. libcaes_crypt_ecb() DECRYPT roundtrip matches plaintext
 *  6. libcaes_crypt_cbc() ENCRYPT+DECRYPT roundtrip matches plaintext
 *  7. tweaked context initialize + set_keys == 1
 *  8. libcaes_crypt_xts() ENCRYPT+DECRYPT roundtrip matches plaintext
 *  9. END-TO-END file workflow: write 64-byte plaintext file ->
 *     AES-128-CBC encrypt to ciphertext file -> decrypt to recovered
 *     file -> byte-compare with original (real file IO, multi-block,
 *     exercises the library as a downstream consumer would use it
 *     for file encryption on HarmonyOS).
 *
 * Any failure exits non-zero so ctest reports failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libcaes.h>

static int total_checks = 0;
static int passed_checks = 0;

#define CHECK(cond, label) do { \
    total_checks++; \
    if (cond) { passed_checks++; printf("PASS: %s\n", label); } \
    else { printf("FAIL: %s\n", label); } \
} while (0)

int main(void)
{
    const char *version = libcaes_get_version();
    CHECK(version != NULL && version[0] != '\0', "get_version non-empty");
    if (version != NULL) {
        printf("libcaes version: %s\n", version);
    }

    libcaes_context_t *context = NULL;
    libcaes_error_t *error = NULL;
    int rc = libcaes_context_initialize(&context, &error);
    CHECK(rc == 1 && context != NULL, "context_initialize");

    /* AES-128 test key 00..0f, plaintext 00..ff pattern. */
    uint8_t key[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
    };
    uint8_t plaintext[16] = {
        0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff
    };
    uint8_t encrypted[16];
    uint8_t decrypted[16];
    uint8_t iv[16];
    memset(iv, 0, sizeof(iv));
    memset(encrypted, 0, sizeof(encrypted));
    memset(decrypted, 0, sizeof(decrypted));

    rc = libcaes_context_set_key(context, LIBCAES_CRYPT_MODE_ENCRYPT,
                                 key, 128, &error);
    CHECK(rc == 1, "context_set_key AES-128 encrypt");

    rc = libcaes_crypt_ecb(context, LIBCAES_CRYPT_MODE_ENCRYPT,
                           plaintext, 16, encrypted, 16, &error);
    CHECK(rc == 1, "crypt_ecb encrypt one block");

    /* ECB decrypt needs a DECRYPT key context; set up a decrypt
     * context for the roundtrip. */
    {
        libcaes_context_t *dctx = NULL;
        libcaes_error_t *derror = NULL;
        int drc = libcaes_context_initialize(&dctx, &derror);
        int ok = 0;
        if (drc == 1) {
            drc = libcaes_context_set_key(dctx, LIBCAES_CRYPT_MODE_DECRYPT,
                                          key, 128, &derror);
            if (drc == 1) {
                drc = libcaes_crypt_ecb(dctx, LIBCAES_CRYPT_MODE_DECRYPT,
                                        encrypted, 16, decrypted, 16, &derror);
                if (drc == 1 && memcmp(decrypted, plaintext, 16) == 0) {
                    ok = 1;
                }
            }
            libcaes_context_free(&dctx, &derror);
        }
        if (derror != NULL) {
            libcaes_error_free(&derror);
        }
        CHECK(ok == 1, "crypt_ecb decrypt roundtrip");
    }

    {
        uint8_t cbc_enc[16], cbc_dec[16];
        uint8_t civ[16];
        memset(civ, 0, sizeof(civ));
        memset(cbc_enc, 0, sizeof(cbc_enc));
        memset(cbc_dec, 0, sizeof(cbc_dec));
        int ok = 0;
        if (libcaes_crypt_cbc(context, LIBCAES_CRYPT_MODE_ENCRYPT,
                              civ, 16, plaintext, 16,
                              cbc_enc, 16, &error) == 1) {
            libcaes_context_t *dctx = NULL;
            libcaes_error_t *derror = NULL;
            if (libcaes_context_initialize(&dctx, &derror) == 1 &&
                libcaes_context_set_key(dctx, LIBCAES_CRYPT_MODE_DECRYPT,
                                        key, 128, &derror) == 1) {
                memset(civ, 0, sizeof(civ));
                if (libcaes_crypt_cbc(dctx, LIBCAES_CRYPT_MODE_DECRYPT,
                                      civ, 16, cbc_enc, 16,
                                      cbc_dec, 16, &derror) == 1 &&
                    memcmp(cbc_dec, plaintext, 16) == 0) {
                    ok = 1;
                }
                libcaes_context_free(&dctx, &derror);
            }
            if (derror != NULL) {
                libcaes_error_free(&derror);
            }
        }
        CHECK(ok == 1, "crypt_cbc roundtrip");
    }

    {
        libcaes_tweaked_context_t *tctx = NULL;
        libcaes_error_t *terror = NULL;
        int ok = 0;
        if (libcaes_context_free(&context, &error) == 1) {
            context = NULL;
        }
        if (libcaes_tweaked_context_initialize(&tctx, &terror) == 1 &&
            libcaes_tweaked_context_set_keys(tctx, LIBCAES_CRYPT_MODE_ENCRYPT,
                                             key, 128, key, 128,
                                             &terror) == 1) {
            ok = 1;
        }
        CHECK(ok == 1, "tweaked_context init+set_keys");
        if (ok == 1) {
            uint8_t tweak[16];
            uint8_t xts_enc[16], xts_dec[16];
            memset(tweak, 0, sizeof(tweak));
            memset(xts_enc, 0, sizeof(xts_enc));
            memset(xts_dec, 0, sizeof(xts_dec));
            int xok = 0;
            if (libcaes_crypt_xts(tctx, LIBCAES_CRYPT_MODE_ENCRYPT,
                                  tweak, 16, plaintext, 16,
                                  xts_enc, 16, &terror) == 1) {
                libcaes_tweaked_context_t *xdt = NULL;
                libcaes_error_t *xerr = NULL;
                if (libcaes_tweaked_context_initialize(&xdt, &xerr) == 1 &&
                    libcaes_tweaked_context_set_keys(
                        xdt, LIBCAES_CRYPT_MODE_DECRYPT,
                        key, 128, key, 128, &xerr) == 1 &&
                    libcaes_crypt_xts(xdt, LIBCAES_CRYPT_MODE_DECRYPT,
                                      tweak, 16, xts_enc, 16,
                                      xts_dec, 16, &xerr) == 1 &&
                    memcmp(xts_dec, plaintext, 16) == 0) {
                    xok = 1;
                }
                if (xdt != NULL) {
                    libcaes_tweaked_context_free(&xdt, &xerr);
                }
                if (xerr != NULL) {
                    libcaes_error_free(&xerr);
                }
            }
            CHECK(xok == 1, "crypt_xts roundtrip");
            libcaes_tweaked_context_free(&tctx, &terror);
        } else {
            total_checks++;
            printf("FAIL: crypt_xts roundtrip (tweaked context unavailable)\n");
            if (tctx != NULL) {
                libcaes_tweaked_context_free(&tctx, &terror);
            }
        }
        if (terror != NULL) {
            libcaes_error_free(&terror);
        }
    }

    if (context != NULL) {
        libcaes_context_free(&context, &error);
    }
    if (error != NULL) {
        libcaes_error_free(&error);
    }

    /* 9. End-to-end consumer workflow: file-level AES-128-CBC
     * encrypt -> decrypt roundtrip through real files, as a
     * downstream HarmonyOS consumer would use libcaes for file
     * protection. Multi-block (64 bytes = 4 AES blocks) so CBC
     * chaining across blocks is exercised, not just a single block.
     * Uses TMPDIR when provided (HMBS/HarmonyOS workers) with CWD
     * fallback. */
    {
        const char *tmpdir = getenv("TMPDIR");
        char plain_path[1024];
        char cipher_path[1024];
        char recovered_path[1024];
        if (tmpdir != NULL && tmpdir[0] != '\0') {
            snprintf(plain_path, sizeof(plain_path), "%s/libcaes_e2e_plain.bin", tmpdir);
            snprintf(cipher_path, sizeof(cipher_path), "%s/libcaes_e2e_cipher.bin", tmpdir);
            snprintf(recovered_path, sizeof(recovered_path), "%s/libcaes_e2e_recovered.bin", tmpdir);
        } else {
            snprintf(plain_path, sizeof(plain_path), "libcaes_e2e_plain.bin");
            snprintf(cipher_path, sizeof(cipher_path), "libcaes_e2e_cipher.bin");
            snprintf(recovered_path, sizeof(recovered_path), "libcaes_e2e_recovered.bin");
        }
        plain_path[sizeof(plain_path) - 1] = '\0';
        cipher_path[sizeof(cipher_path) - 1] = '\0';
        recovered_path[sizeof(recovered_path) - 1] = '\0';

        uint8_t file_plain[64];
        uint8_t file_cipher[64];
        uint8_t file_recovered[64];
        uint8_t file_iv[16];
        size_t i;
        for (i = 0; i < sizeof(file_plain); i++) {
            file_plain[i] = (uint8_t)((i * 37u + 11u) & 0xffu);
        }
        memset(file_cipher, 0, sizeof(file_cipher));
        memset(file_recovered, 0, sizeof(file_recovered));
        memset(file_iv, 0, sizeof(file_iv));

        int e2e_ok = 0;
        libcaes_context_t *ectx = NULL;
        libcaes_error_t *eerror = NULL;
        FILE *fp = NULL;
        /* Step 1: materialize plaintext file (consumer input). */
        fp = fopen(plain_path, "wb");
        if (fp != NULL) {
            size_t written = fwrite(file_plain, 1, sizeof(file_plain), fp);
            fclose(fp);
            fp = NULL;
            if (written == sizeof(file_plain)) {
                /* Step 2: read back + CBC-encrypt in one shot. */
                uint8_t read_back[64];
                fp = fopen(plain_path, "rb");
                if (fp != NULL) {
                    size_t got = fread(read_back, 1, sizeof(read_back), fp);
                    fclose(fp);
                    fp = NULL;
                    if (got == sizeof(read_back) &&
                        memcmp(read_back, file_plain, sizeof(file_plain)) == 0 &&
                        libcaes_context_initialize(&ectx, &eerror) == 1 &&
                        libcaes_context_set_key(ectx, LIBCAES_CRYPT_MODE_ENCRYPT,
                                                key, 128, &eerror) == 1 &&
                        libcaes_crypt_cbc(ectx, LIBCAES_CRYPT_MODE_ENCRYPT,
                                          file_iv, 16, read_back, sizeof(read_back),
                                          file_cipher, sizeof(file_cipher),
                                          &eerror) == 1) {
                        /* Step 3: persist ciphertext file. */
                        fp = fopen(cipher_path, "wb");
                        if (fp != NULL) {
                            size_t cw = fwrite(file_cipher, 1, sizeof(file_cipher), fp);
                            fclose(fp);
                            fp = NULL;
                            if (cw == sizeof(file_cipher)) {
                                libcaes_context_free(&ectx, &eerror);
                                ectx = NULL;
                                /* Step 4: decrypt from ciphertext file. */
                                uint8_t cipher_back[64];
                                fp = fopen(cipher_path, "rb");
                                if (fp != NULL) {
                                    size_t cg = fread(cipher_back, 1, sizeof(cipher_back), fp);
                                    fclose(fp);
                                    fp = NULL;
                                    if (cg == sizeof(cipher_back)) {
                                        libcaes_context_t *ddctx = NULL;
                                        libcaes_error_t *dderror = NULL;
                                        uint8_t div[16];
                                        memset(div, 0, sizeof(div));
                                        if (libcaes_context_initialize(&ddctx, &dderror) == 1 &&
                                            libcaes_context_set_key(ddctx, LIBCAES_CRYPT_MODE_DECRYPT,
                                                                    key, 128, &dderror) == 1 &&
                                            libcaes_crypt_cbc(ddctx, LIBCAES_CRYPT_MODE_DECRYPT,
                                                              div, 16, cipher_back, sizeof(cipher_back),
                                                              file_recovered, sizeof(file_recovered),
                                                              &dderror) == 1 &&
                                            memcmp(file_recovered, file_plain, sizeof(file_plain)) == 0) {
                                            /* Step 5: persist + verify recovered file. */
                                            fp = fopen(recovered_path, "wb");
                                            if (fp != NULL) {
                                                size_t rw = fwrite(file_recovered, 1, sizeof(file_recovered), fp);
                                                fclose(fp);
                                                fp = NULL;
                                                if (rw == sizeof(file_recovered)) {
                                                    uint8_t verify[64];
                                                    fp = fopen(recovered_path, "rb");
                                                    if (fp != NULL) {
                                                        size_t vg = fread(verify, 1, sizeof(verify), fp);
                                                        fclose(fp);
                                                        fp = NULL;
                                                        if (vg == sizeof(verify) &&
                                                            memcmp(verify, file_plain, sizeof(file_plain)) == 0 &&
                                                            memcmp(file_cipher, file_plain, sizeof(file_plain)) != 0) {
                                                            e2e_ok = 1;
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                        if (ddctx != NULL) {
                                            libcaes_context_free(&ddctx, &dderror);
                                        }
                                        if (dderror != NULL) {
                                            libcaes_error_free(&dderror);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        if (ectx != NULL) {
            libcaes_context_free(&ectx, &eerror);
        }
        if (eerror != NULL) {
            libcaes_error_free(&eerror);
        }
        remove(plain_path);
        remove(cipher_path);
        remove(recovered_path);
        CHECK(e2e_ok == 1, "file_cbc_e2e encrypt-decrypt via files");
    }

    printf("libcaes consumer checks: %d/%d passed\n", passed_checks, total_checks);
    return (passed_checks == total_checks && total_checks == 9) ? 0 : 1;
}
