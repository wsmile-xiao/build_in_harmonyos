/*
 * test_openssl.c -- OpenSSL 3.5.7 L1 comprehensive test
 *
 * Test coverage:
 *   T1  Version detection
 *   T2  SHA family (SHA224/256/384/512)
 *   T3  MD5 + SHA1 legacy hashes
 *   T4  HMAC-SHA256
 *   T5  AES-256-CBC encrypt/decrypt (PKCS7 padding)
 *   T6  AES-256-GCM authenticated encryption
 *   T7  RSA-2048 key generation + encrypt/decrypt
 *   T8  EC P-256 sign / verify
 *   T9  RAND_bytes entropy
 *   T10 Error queue
 *   T11 TLS 1.3 context creation
 *   T12 X.509 certificate parsing
 *
 * Expected upstream results: 12/12 pass.
 * Platform-adapted: OHOS(musl) bash wrapper via CONFIG_SHELL.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <openssl/ssl.h>
#include <openssl/sha.h>
#include <openssl/md5.h>
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/ec.h>
#include <openssl/ecdsa.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/x509_vfy.h>

/* -- helpers ----------------------------------------------------------- */

static int g_total = 0, g_passed = 0;

static void print_result(const char *name, int ok) {
    printf("[%s] %s\n", ok ? "PASS" : "FAIL", name);
    g_total++; if (ok) g_passed++;
}

/* -- T1  Version ------------------------------------------------------ */

static void test_version(void) {
    unsigned long ver = OpenSSL_version_num();
    const char *txt = OpenSSL_version(OPENSSL_VERSION);
    int ok = txt != NULL && strstr(txt, "3.5.") != NULL;
    printf("  version: %s (0x%lx)\n", txt, ver);
    print_result("T1  OpenSSL version contains 3.5.x", ok);
}

/* -- T2  SHA-2 family ------------------------------------------------- */

static void test_sha2_family(void) {
    const unsigned char msg[] = "test vector for SHA family";
    unsigned char d224[SHA224_DIGEST_LENGTH];
    unsigned char d256[SHA256_DIGEST_LENGTH];
    unsigned char d384[SHA384_DIGEST_LENGTH];
    unsigned char d512[SHA512_DIGEST_LENGTH];

    SHA224(msg, sizeof(msg) - 1, d224);
    SHA256(msg, sizeof(msg) - 1, d256);
    SHA384(msg, sizeof(msg) - 1, d384);
    SHA512(msg, sizeof(msg) - 1, d512);

    int ok224 = (d224[0] != 0 || d224[SHA224_DIGEST_LENGTH - 1] != 0);
    int ok256 = (d256[0] != 0 || d256[SHA256_DIGEST_LENGTH - 1] != 0);
    int ok384 = (d384[0] != 0 || d384[SHA384_DIGEST_LENGTH - 1] != 0);
    int ok512 = (d512[0] != 0 || d512[SHA512_DIGEST_LENGTH - 1] != 0);

    /* KAT: SHA-256("abc") */
    static const unsigned char sha256_abc[SHA256_DIGEST_LENGTH] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };
    unsigned char kat[SHA256_DIGEST_LENGTH];
    SHA256((const unsigned char *)"abc", 3, kat);
    int kat_ok = memcmp(kat, sha256_abc, SHA256_DIGEST_LENGTH) == 0;

    printf("  SHA-224=%d SHA-256=%d SHA-384=%d SHA-512=%d KAT=%d\n",
           ok224, ok256, ok384, ok512, kat_ok);

    print_result("T2  SHA-2 family + SHA-256 KAT", ok224 && ok256 && ok384 && ok512 && kat_ok);
}

/* -- T3  Legacy hashes (MD5 / SHA-1) ---------------------------------- */

static void test_legacy_hashes(void) {
    unsigned char md5out[MD5_DIGEST_LENGTH];
    unsigned char sha1out[SHA_DIGEST_LENGTH];
    const unsigned char msg[] = "legacy hash test";

    MD5(msg, sizeof(msg) - 1, md5out);
    SHA1(msg, sizeof(msg) - 1, sha1out);

    int ok_md5  = (md5out[0]  != 0 || md5out[MD5_DIGEST_LENGTH - 1]  != 0);
    int ok_sha1 = (sha1out[0] != 0 || sha1out[SHA_DIGEST_LENGTH - 1] != 0);

    printf("  MD5:   non-trivial=%d\n", ok_md5);
    printf("  SHA-1: non-trivial=%d\n", ok_sha1);
    print_result("T3  Legacy hashes MD5 + SHA-1", ok_md5 && ok_sha1);
}

/* -- T4  HMAC-SHA256 ------------------------------------------------- */

static void test_hmac_sha256(void) {
    const unsigned char key[] = "hmac-test-secret-key-32b-long!!";
    const unsigned char data[] = "message to authenticate";
    unsigned char out[EVP_MAX_MD_SIZE];
    unsigned int outlen = 0;

    HMAC(EVP_sha256(), key, sizeof(key) - 1, data, sizeof(data) - 1, out, &outlen);

    /* KAT: HMAC-SHA256(key="key", data="The quick brown fox jumps over the lazy dog") */
    static const unsigned char kat1[SHA256_DIGEST_LENGTH] = {
        0xf7, 0xbc, 0x83, 0xf4, 0x30, 0x53, 0x84, 0x24,
        0xb1, 0x32, 0x98, 0xe6, 0xaa, 0x6f, 0xb1, 0x43,
        0xef, 0x4d, 0x59, 0xa1, 0x49, 0x46, 0x17, 0x59,
        0x97, 0x47, 0x9d, 0xbc, 0x2d, 0x1a, 0x3c, 0xd8
    };
    /* KAT2: key="key", data="" (empty) */
    static const unsigned char kat2[SHA256_DIGEST_LENGTH] = {
        0x5d, 0x5d, 0x13, 0x95, 0x63, 0xc9, 0x5b, 0x59,
        0x67, 0xb9, 0xbd, 0x9a, 0x8c, 0x9b, 0x23, 0x3a,
        0x9d, 0xed, 0xb4, 0x50, 0x72, 0x79, 0x4c, 0xd2,
        0x32, 0xdc, 0x1b, 0x74, 0x83, 0x26, 0x07, 0xd0
    };

    const unsigned char *kat1_key = (const unsigned char *)"key";
    const unsigned char *kat1_data = (const unsigned char *)"The quick brown fox jumps over the lazy dog";
    unsigned char kat1_out[EVP_MAX_MD_SIZE], kat2_out[EVP_MAX_MD_SIZE];
    unsigned int kat1_len = 0, kat2_len = 0;
    HMAC(EVP_sha256(), kat1_key, 3, kat1_data, 43, kat1_out, &kat1_len);
    HMAC(EVP_sha256(), kat1_key, 3, (const unsigned char *)"", 0, kat2_out, &kat2_len);

    int kat_ok1 = (kat1_len == SHA256_DIGEST_LENGTH) && (memcmp(kat1_out, kat1, SHA256_DIGEST_LENGTH) == 0);
    int kat_ok2 = (kat2_len == SHA256_DIGEST_LENGTH) && (memcmp(kat2_out, kat2, SHA256_DIGEST_LENGTH) == 0);

    int ok = (outlen == 32) && kat_ok1 && kat_ok2;
    printf("  HMAC-SHA256 outlen=%u, KAT1=%d, KAT2=%d\n", outlen, kat_ok1, kat_ok2);
    print_result("T4  HMAC-SHA256 (RFC 4231 KAT vectors)", ok);
}

/* -- T5  AES-256-CBC encrypt / decrypt ------------------------------- */

static void test_aes_cbc(void) {
    const unsigned char key[32] = {0};
    const unsigned char iv[16] = {0};
    const unsigned char pt[16] = "AES-256-CBC test";

    unsigned char ct[32];
    unsigned char dt[32];

    EVP_CIPHER_CTX *ectx = EVP_CIPHER_CTX_new();
    EVP_CIPHER_CTX *dctx = EVP_CIPHER_CTX_new();
    if (!ectx || !dctx) {
        EVP_CIPHER_CTX_free(ectx);
        EVP_CIPHER_CTX_free(dctx);
        print_result("T5  AES-256-CBC encrypt/decrypt", 0);
        return;
    }

    int outl = 0, inl = 0, rc = 0;

    EVP_EncryptInit_ex(ectx, EVP_aes_256_cbc(), NULL, key, iv);
    if (EVP_EncryptUpdate(ectx, ct, &outl, pt, sizeof(pt)) == 1) {
        if (EVP_EncryptFinal_ex(ectx, ct + outl, &inl) == 1) {
            outl += inl;
            EVP_DecryptInit_ex(dctx, EVP_aes_256_cbc(), NULL, key, iv);
            int d_outl = 0, d_inl = 0;
            if (EVP_DecryptUpdate(dctx, dt, &d_outl, ct, outl) == 1) {
                if (EVP_DecryptFinal_ex(dctx, dt + d_outl, &d_inl) == 1) {
                    d_outl += d_inl;
                    rc = (d_outl == (int)sizeof(pt)) && (memcmp(dt, pt, sizeof(pt)) == 0);
                }
            }
            printf("  ct_size=%d, decrypted=%d, match=%d\n", outl, d_outl, rc);
        }
    }

    EVP_CIPHER_CTX_free(ectx);
    EVP_CIPHER_CTX_free(dctx);
    print_result("T5  AES-256-CBC encrypt/decrypt", rc);
}

/* -- T6  AES-256-GCM authenticated encryption ----------------------- */

static void test_aes_gcm(void) {
    const unsigned char key[32] = {0};
    const unsigned char iv[12] = {0};
    const unsigned char aad[] = "additional authenticated data";
    const unsigned char pt[] = "GCM plaintext test";
    unsigned char ct[64], tag[16], dt[64];

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) { print_result("T6  AES-256-GCM", 0); return; }

    int outl = 0, inl = 0, tag_ok = 0, dec_ok = 0;

    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, NULL);
    EVP_EncryptInit_ex(ctx, NULL, NULL, key, iv);
    EVP_EncryptUpdate(ctx, NULL, &outl, aad, sizeof(aad) - 1);
    EVP_EncryptUpdate(ctx, ct, &outl, pt, sizeof(pt) - 1);
    EVP_EncryptFinal_ex(ctx, ct + outl, &inl);
    outl += inl;
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag);

    /* decrypt and verify tag */
    EVP_DecryptInit_ex(ctx, NULL, NULL, key, iv);
    EVP_DecryptUpdate(ctx, NULL, &inl, aad, sizeof(aad) - 1);
    EVP_DecryptUpdate(ctx, dt, &outl, ct, outl);
    /* Required: set expected authentication tag before Final */
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, tag);
    dec_ok = EVP_DecryptFinal_ex(ctx, dt + outl, &inl);

    EVP_CIPHER_CTX_free(ctx);

    /* Verify decrypted plaintext matches */
    int pt_match = (outl == (int)(sizeof(pt) - 1)) &&
                   (memcmp(dt, pt, sizeof(pt) - 1) == 0);

    tag_ok = (tag[0] != 0 || tag[15] != 0);
    int ok = tag_ok && dec_ok && pt_match;
    printf("  tag non-zero=%d, decrypt ok=%d, pt_match=%d, ct_size=%d\n", tag_ok, dec_ok, pt_match, outl);
    print_result("T6  AES-256-GCM AEAD (SET_TAG + plaintext match)", ok);
}

/* -- T7  RSA-2048 key gen + encrypt / decrypt ---------------------- */

static void test_rsa_2048(void) {
    RSA *rsa = RSA_new();
    if (!rsa) { print_result("T7  RSA-2048", 0); return; }

    BIGNUM *e = BN_new();
    BN_set_word(e, 65537);
    int ok = 0;

    if (RSA_generate_key_ex(rsa, 2048, e, NULL)) {
        int rsa_size = RSA_size(rsa);
        unsigned char pt[200];
        unsigned char ct[256];
        unsigned char dt[256];
        memset(pt, 0xAB, sizeof(pt));

        int clen = RSA_public_encrypt(sizeof(pt), pt, ct, rsa, RSA_PKCS1_OAEP_PADDING);
        if (clen > 0) {
            int dlen = RSA_private_decrypt(clen, ct, dt, rsa, RSA_PKCS1_OAEP_PADDING);
            ok = (dlen == (int)sizeof(pt)) && (memcmp(pt, dt, sizeof(pt)) == 0);
            printf("  RSA-2048 size=%d, enc=%d, dec=%d, match=%d\n", rsa_size, clen, dlen, ok);
        } else {
            printf("  RSA-2048 encrypt failed: %d\n", clen);
        }
    } else {
        printf("  RSA_generate_key_ex failed\n");
    }

    BN_free(e);
    RSA_free(rsa);
    print_result("T7  RSA-2048 encrypt/decrypt (OAEP)", ok);
}

/* -- T8  EC P-256 sign / verify ----------------------------------- */

static void test_ec_p256(void) {
    EC_KEY *key = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
    if (!key) { print_result("T8  EC P-256 sign/verify", 0); return; }

    if (!EC_KEY_generate_key(key)) {
        EC_KEY_free(key);
        print_result("T8  EC P-256 sign/verify", 0);
        return;
    }

    const unsigned char msg[] = "ECDSA test message";
    unsigned char sig[256];
    unsigned int siglen = sizeof(sig);

    int sign_ok = ECDSA_sign(0, msg, sizeof(msg) - 1, sig, &siglen, key);
    int verify_ok = ECDSA_verify(0, msg, sizeof(msg) - 1, sig, siglen, key) == 1;

    /* Negative test: verify signature fails when message is altered */
    int tamper_fail = -1;
    if (sign_ok) {
        /* Mutate a single byte of the message - valid signature must reject */
        unsigned char bad_msg[] = "ECDSA test message!";
        tamper_fail = ECDSA_verify(0, bad_msg, sizeof(bad_msg) - 1, sig, siglen, key);
    }

    EC_KEY_free(key);

    int ok = sign_ok && verify_ok && (tamper_fail == 0);
    printf("  sign=%d, verify_ok=%d, tamper_rejected=%d\n",
           sign_ok, verify_ok, (tamper_fail == 0));
    print_result("T8  EC P-256 sign/verify (with tamper test)", ok);
}

/* -- T9  RAND_bytes entropy --------------------------------------- */

static void test_rand_bytes(void) {
    unsigned char buf1[32], buf2[32];
    RAND_bytes(buf1, sizeof(buf1));
    RAND_bytes(buf2, sizeof(buf2));

    int nonzero = 0, different = 0;
    for (int i = 0; i < 32; i++) {
        if (buf1[i] != 0) nonzero++;
        if (buf1[i] != buf2[i]) different++;
    }

    /* 期望 32 字节里约 0.125 个 0；阈值取 24 既保留"输出不是全零/常量"的熵有效性，
       又不会因单次采样出现 0 字节而随机误判（要求 nonzero==32 时误失败率约 11.8%）。 */
    int ok = (nonzero >= 24) && (different >= 16);
    printf("  non-zero bytes=%d/32, different from 2nd call=%d/32\n", nonzero, different);
    print_result("T9  RAND_bytes entropy", ok);
}

/* -- T10 Error queue --------------------------------------------- */

static void test_error_queue(void) {
    ERR_clear_error();

    /* Push a synthetic error */
    ERR_put_error(ERR_LIB_USER, 0, ERR_R_MALLOC_FAILURE, __FILE__, __LINE__);

    unsigned long e = ERR_get_error();
    int ok = (e != 0);
    if (ok) {
        char buf[128];
        ERR_error_string(e, buf);
        printf("  error code: 0x%lx, string: %.50s\n", e, buf);
    } else {
        printf("  error queue empty (unexpected)\n");
    }
    ERR_clear_error();

    print_result("T10 Error queue", ok);
}

/* -- T11 TLS 1.3 context ----------------------------------------- */

static void test_tls_context(void) {
    SSL_library_init();
    SSL_CTX *ctx = SSL_CTX_new(TLS_method());
    if (!ctx) { print_result("T11 TLS context", 0); return; }

    int min_ok = SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
    int max_ok = SSL_CTX_set_max_proto_version(ctx, TLS_MAX_VERSION);

    const SSL_METHOD *m = SSL_CTX_get_ssl_method(ctx);
    SSL *ssl = SSL_new(ctx);
    int ssl_ok = (ssl != NULL && m != NULL);

    if (ssl) SSL_free(ssl);
    SSL_CTX_free(ctx);

    int ok = min_ok && max_ok && ssl_ok;
    printf("  min_tls13=%d, max_default=%d, ssl_obj=%s\n",
           min_ok, max_ok, ssl_ok ? "ok" : "NULL");
    print_result("T11 TLS 1.3 context configuration", ok);
}

/* -- T12 X.509 certificate (self-signed) ------------------------- */

static void test_x509_selfsigned(void) {
    RSA *rsa = RSA_new();
    BIGNUM *e = BN_new();
    BN_set_word(e, 65537);
    if (!RSA_generate_key_ex(rsa, 2048, e, NULL)) {
        BN_free(e);
        RSA_free(rsa);
        print_result("T12 X.509 self-signed cert", 0);
        return;
    }

    X509 *cert = X509_new();
    EVP_PKEY *pkey = EVP_PKEY_new();
    EVP_PKEY_assign_RSA(pkey, rsa); /* RSA is freed with pkey */

    ASN1_INTEGER *serial = ASN1_INTEGER_new();
    ASN1_INTEGER_set(serial, 1);

    X509_set_version(cert, 2); /* v3 */
    X509_set_pubkey(cert, pkey);
    X509_set_serialNumber(cert, serial);

    X509_gmtime_adj(X509_get_notBefore(cert), 0);
    X509_gmtime_adj(X509_get_notAfter(cert), 60 * 60 * 24);

    int sign_ok = X509_sign(cert, pkey, EVP_sha256()) > 0;
    int verify_ok = (sign_ok && X509_verify(cert, pkey) == 1);

    int sig_len = sign_ok ? EVP_PKEY_size(pkey) : 0;
    int ok = sign_ok && verify_ok;
    if (ok) {
        printf("  cert signed (EVP_PKEY_size=%d) and verified OK\n", sig_len);
    }

    ASN1_INTEGER_free(serial);
    EVP_PKEY_free(pkey);
    X509_free(cert);
    BN_free(e);

    print_result("T12 X.509 self-signed certificate (sign+verify)", ok);
}

/* -- main ---------------------------------------------------------- */

int main(void) {
    printf("=== OpenSSL 3.5.7 Comprehensive Test Suite ===\n\n");

    test_version();
    test_sha2_family();
    test_legacy_hashes();
    test_hmac_sha256();
    test_aes_cbc();
    test_aes_gcm();
    test_rsa_2048();
    test_ec_p256();
    test_rand_bytes();
    test_error_queue();
    test_tls_context();
    test_x509_selfsigned();

    printf("\n=== Results: %d/%d tests passed ===\n", g_passed, g_total);
    printf("OpenSSL version: %s\n", OpenSSL_version(OPENSSL_VERSION));
    return (g_passed == g_total) ? 0 : 1;
}
