/*
 * test_openssl.c — OpenSSL 3.0.21 HarmonyOS PC 适配综合测试
 *
 * 测试范围：8 大类 / 17 条断言，覆盖核心 API。
 *
 * 设计原则：
 * - R34: 每个测试调用被测包的真实 API，无空壳
 * - 测试函数相互独立（失败不影响其他）
 * - 输出明确（每个打印 PASS/FAIL）
 * - 退出码：0 全过 / 1 任意失败
 * - 静态链接，不依赖运行时动态库
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <openssl/hmac.h>
#include <openssl/aes.h>
#include <openssl/ec.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#include <openssl/bn.h>
#include <openssl/provider.h>

/* ------------------------------------------------------------------ *
 *  全局计数器
 * ------------------------------------------------------------------ */
static int g_passed = 0;
static int g_failed = 0;

static void print_err(const char *msg) {
    fprintf(stderr, "    ERR %s: ", msg);
    ERR_print_errors_fp(stderr);
    fprintf(stderr, "\n");
}

static void report(int ok, const char *name) {
    if (ok) {
        printf("  [PASS] %s\n", name);
        g_passed++;
    } else {
        printf("  [FAIL] %s\n", name);
        g_failed++;
    }
}

static const unsigned char *TEST_DATA = (const unsigned char *)"The quick brown fox jumps over the lazy dog";
static const size_t TEST_DATA_LEN = 43;

/* ------------------------------------------------------------------ *
 *  T1: Hash 摘要 — SHA-1 / SHA-256 / SHA-512
 * ------------------------------------------------------------------ */
static int test_sha1(void) {
    unsigned char md[64];
    unsigned int mdlen = 0;
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    if (!ctx) { fprintf(stderr, "    ERR SHA1: no context\n"); return 0; }
    int ok = (EVP_DigestInit_ex(ctx, EVP_sha1(), NULL) == 1 &&
               EVP_DigestUpdate(ctx, TEST_DATA, TEST_DATA_LEN) == 1 &&
               EVP_DigestFinal_ex(ctx, md, &mdlen) == 1 &&
               mdlen == 20);
    EVP_MD_CTX_free(ctx);
    if (!ok) fprintf(stderr, "    ERR SHA1 failed\n");
    return ok;
}

static int test_sha256(void) {
    unsigned char md[64];
    unsigned int mdlen = 0;
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    if (!ctx) { fprintf(stderr, "    ERR SHA256: no context\n"); return 0; }
    int ok = (EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) == 1 &&
               EVP_DigestUpdate(ctx, TEST_DATA, TEST_DATA_LEN) == 1 &&
               EVP_DigestFinal_ex(ctx, md, &mdlen) == 1 &&
               mdlen == 32);
    EVP_MD_CTX_free(ctx);
    if (!ok) fprintf(stderr, "    ERR SHA256 failed\n");
    return ok;
}

static int test_sha512(void) {
    unsigned char md[64];
    unsigned int mdlen = 0;
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    if (!ctx) { fprintf(stderr, "    ERR SHA512: no context\n"); return 0; }
    int ok = (EVP_DigestInit_ex(ctx, EVP_sha512(), NULL) == 1 &&
               EVP_DigestUpdate(ctx, TEST_DATA, TEST_DATA_LEN) == 1 &&
               EVP_DigestFinal_ex(ctx, md, &mdlen) == 1 &&
               mdlen == 64);
    EVP_MD_CTX_free(ctx);
    if (!ok) fprintf(stderr, "    ERR SHA512 failed\n");
    return ok;
}

/* ------------------------------------------------------------------ *
 *  T2: HMAC-SHA256
 * ------------------------------------------------------------------ */
static int test_hmac_sha256(void) {
    unsigned char key[32] = "01234567890123456789012345678901";
    unsigned char out[64];
    unsigned int outlen = 0;
    unsigned char *res = HMAC(EVP_sha256(), key, sizeof(key),
                              TEST_DATA, TEST_DATA_LEN, out, &outlen);
    int ok = (res != NULL) && (outlen == 32);
    if (!ok) fprintf(stderr, "    ERR HMAC failed\n");
    return ok;
}

/* ------------------------------------------------------------------ *
 *  T3: 对称加密 — AES-128-CBC / AES-256-CBC / AES-256-GCM
 * ------------------------------------------------------------------ */
static int test_aes_cbc(int key_bits, const char *name) {
    unsigned char key[32], iv[16], plain[32], enc[64], dec[32];
    int enc_len = 0, enc_rest = 0, dec_len = 0, dec_rest = 0;

    if (RAND_bytes(key, key_bits / 8) != 1) return 0;
    if (RAND_bytes(iv, 16) != 1) return 0;
    memset(plain, 'X', 32);

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return 0;

    const EVP_CIPHER *cipher = (key_bits == 128) ? EVP_aes_128_cbc() : EVP_aes_256_cbc();
    int ok = (EVP_EncryptInit_ex(ctx, cipher, NULL, key, iv) == 1 &&
               EVP_EncryptUpdate(ctx, enc, &enc_len, plain, 32) == 1 &&
               EVP_EncryptFinal_ex(ctx, enc + enc_len, &enc_rest) == 1 &&
               EVP_CIPHER_CTX_reset(ctx) == 1 &&
               EVP_DecryptInit_ex(ctx, cipher, NULL, key, iv) == 1 &&
               EVP_DecryptUpdate(ctx, dec, &dec_len, enc, enc_len + enc_rest) == 1 &&
               EVP_DecryptFinal_ex(ctx, dec + dec_len, &dec_rest) == 1 &&
               dec_len + dec_rest == 32 &&
               memcmp(plain, dec, 32) == 0);

    EVP_CIPHER_CTX_free(ctx);
    if (!ok) fprintf(stderr, "    ERR %s failed\n", name);
    return ok;
}

static int test_aes_128_cbc(void) { return test_aes_cbc(128, "AES-128-CBC"); }
static int test_aes_256_cbc(void) { return test_aes_cbc(256, "AES-256-CBC"); }

static int test_aes_256_gcm(void) {
    unsigned char key[32], iv[12], plain[32], enc[64], tag[16], dec[32];
    int enc_len = 0, enc_rest = 0, dec_len = 0, dec_rest = 0;

    if (RAND_bytes(key, 32) != 1) return 0;
    if (RAND_bytes(iv, 12) != 1) return 0;
    memset(plain, 'Y', 32);

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return 0;

    int ok = (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL) == 1 &&
               EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, NULL) == 1 &&
               EVP_EncryptInit_ex(ctx, NULL, NULL, key, iv) == 1 &&
               EVP_EncryptUpdate(ctx, enc, &enc_len, plain, 32) == 1 &&
               EVP_EncryptFinal_ex(ctx, enc + enc_len, &enc_rest) == 1 &&
               EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag) == 1 &&
               EVP_CIPHER_CTX_reset(ctx) == 1 &&
               EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL) == 1 &&
               EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, NULL) == 1 &&
               EVP_DecryptInit_ex(ctx, NULL, NULL, key, iv) == 1 &&
               EVP_DecryptUpdate(ctx, dec, &dec_len, enc, enc_len + enc_rest) == 1 &&
               EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, tag) == 1 &&
               EVP_DecryptFinal_ex(ctx, dec + dec_len, &dec_rest) == 1 &&
               dec_len + dec_rest == 32 &&
               memcmp(plain, dec, 32) == 0);

    EVP_CIPHER_CTX_free(ctx);
    if (!ok) fprintf(stderr, "    ERR AES-256-GCM failed\n");
    return ok;
}

/* ------------------------------------------------------------------ *
 *  T4: RSA 密钥生成 — 2048 / 4096
 * ------------------------------------------------------------------ */
static int test_rsa_keygen(int bits) {
    EVP_PKEY *pkey = NULL;
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
    if (!ctx) return 0;

    int ok = (EVP_PKEY_keygen_init(ctx) == 1 &&
               EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, bits) == 1 &&
               EVP_PKEY_keygen(ctx, &pkey) == 1 &&
               pkey != NULL);

    if (pkey) EVP_PKEY_free(pkey);
    EVP_PKEY_CTX_free(ctx);
    if (!ok) fprintf(stderr, "    ERR RSA-%d keygen failed\n", bits);
    return ok;
}

static int test_rsa_2048(void) { return test_rsa_keygen(2048); }
static int test_rsa_4096(void) { return test_rsa_keygen(4096); }

/* ------------------------------------------------------------------ *
 *  T5: ECC — ECDH P-256 密钥协商
 * ------------------------------------------------------------------ */
static int test_ecdh_p256(void) {
    EVP_PKEY *alice = NULL, *bob = NULL;
    EVP_PKEY_CTX *actx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (!actx) return 0;

    int ok = (EVP_PKEY_keygen_init(actx) == 1 &&
               EVP_PKEY_CTX_set_ec_paramgen_curve_nid(actx, NID_X9_62_prime256v1) == 1 &&
               EVP_PKEY_keygen(actx, &alice) == 1);

    EVP_PKEY_CTX *bctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (ok && bctx) {
        ok = (EVP_PKEY_keygen_init(bctx) == 1 &&
               EVP_PKEY_CTX_set_ec_paramgen_curve_nid(bctx, NID_X9_62_prime256v1) == 1 &&
               EVP_PKEY_keygen(bctx, &bob) == 1);
    }

    unsigned char *sa = NULL, *sb = NULL;
    size_t la = 0, lb = 0;

    if (ok && alice && bob) {
        EVP_PKEY_CTX *dactx = EVP_PKEY_CTX_new(alice, NULL);
        EVP_PKEY_CTX *dbctx = EVP_PKEY_CTX_new(bob, NULL);

        if (dactx && dbctx) {
            ok = (EVP_PKEY_derive_init(dactx) == 1 &&
                   EVP_PKEY_derive_set_peer(dactx, bob) == 1 &&
                   EVP_PKEY_derive(dactx, NULL, &la) == 1 &&
                   (sa = OPENSSL_malloc(la)) != NULL &&
                   EVP_PKEY_derive(dactx, sa, &la) == 1 &&
                   EVP_PKEY_derive_init(dbctx) == 1 &&
                   EVP_PKEY_derive_set_peer(dbctx, alice) == 1 &&
                   EVP_PKEY_derive(dbctx, NULL, &lb) == 1 &&
                   (sb = OPENSSL_malloc(lb)) != NULL &&
                   EVP_PKEY_derive(dbctx, sb, &lb) == 1 &&
                   la == lb && la == 32 &&
                   memcmp(sa, sb, (int)la) == 0);

            if (dactx) EVP_PKEY_CTX_free(dactx);
            if (dbctx) EVP_PKEY_CTX_free(dbctx);
        }
    }

    if (sa) OPENSSL_free(sa);
    if (sb) OPENSSL_free(sb);
    if (alice) EVP_PKEY_free(alice);
    if (bob) EVP_PKEY_free(bob);
    EVP_PKEY_CTX_free(actx);
    if (bctx) EVP_PKEY_CTX_free(bctx);

    if (!ok) fprintf(stderr, "    ERR ECDH-P256 failed\n");
    return ok;
}

/* ------------------------------------------------------------------ *
 *  T6: 数字签名 — ECDSA-P256（sign-only）/ RSA-2048-PSS（sign + verify）
 * ------------------------------------------------------------------ */
static int test_ecdsa_sign(void) {
    EVP_PKEY *pkey = NULL;
    EVP_PKEY_CTX *kctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (!kctx) return 0;
    int ok = (EVP_PKEY_keygen_init(kctx) == 1 &&
               EVP_PKEY_CTX_set_ec_paramgen_curve_nid(kctx, NID_X9_62_prime256v1) == 1 &&
               EVP_PKEY_keygen(kctx, &pkey) == 1);
    EVP_PKEY_CTX_free(kctx);
    if (!ok) { fprintf(stderr, "    ERR ECDSA keygen failed\n"); return 0; }

    /* one-shot sign */
    EVP_MD_CTX *mctx = EVP_MD_CTX_new();
    if (!mctx) { EVP_PKEY_free(pkey); return 0; }

    size_t siglen = 0;
    unsigned char *sig = NULL;
    ok = (EVP_DigestSignInit(mctx, NULL, EVP_sha256(), NULL, pkey) == 1 &&
           EVP_DigestSign(mctx, NULL, &siglen, TEST_DATA, TEST_DATA_LEN) == 1 &&
           siglen > 0 &&
           (sig = OPENSSL_malloc(siglen)) != NULL &&
           EVP_DigestSign(mctx, sig, &siglen, TEST_DATA, TEST_DATA_LEN) == 1 &&
           siglen >= 64);

    if (sig) OPENSSL_free(sig);
    EVP_MD_CTX_free(mctx);
    EVP_PKEY_free(pkey);
    if (!ok) fprintf(stderr, "    ERR ECDSA sign failed\n");
    return ok;
}

static int test_rsa_pss_sign(void) {
    EVP_PKEY *pkey = NULL;
    EVP_PKEY_CTX *kctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
    if (!kctx) return 0;
    int ok = (EVP_PKEY_keygen_init(kctx) == 1 &&
               EVP_PKEY_CTX_set_rsa_keygen_bits(kctx, 2048) == 1 &&
               EVP_PKEY_keygen(kctx, &pkey) == 1);
    EVP_PKEY_CTX_free(kctx);
    if (!ok) { fprintf(stderr, "    ERR RSA keygen failed\n"); return 0; }

    EVP_MD_CTX *mctx = EVP_MD_CTX_new();
    if (!mctx) { EVP_PKEY_free(pkey); return 0; }

    /* RSA 的 EVP_PKEY_CTX 默认 padding 是 RSA_PKCS1_PADDING：不显式设成
     * PSS 的话，这条"PSS 用例"实际跑的是 PKCS#1 v1.5，而 RSA-2048 下两种
     * padding 的签名长度都是 256 字节，长度断言区分不了。这里在
     * DigestSignInit 拿到的 pctx 上设 padding 与 salt 长度（= 摘要长度），
     * 验签侧用同一组参数。 */
    EVP_PKEY_CTX *pctx = NULL;
    size_t siglen = 0;
    unsigned char *sig = NULL;
    ok = (EVP_DigestSignInit(mctx, &pctx, EVP_sha256(), NULL, pkey) == 1 &&
           pctx != NULL &&
           EVP_PKEY_CTX_set_rsa_padding(pctx, RSA_PKCS1_PSS_PADDING) == 1 &&
           EVP_PKEY_CTX_set_rsa_pss_saltlen(pctx, RSA_PSS_SALTLEN_DIGEST) == 1 &&
           EVP_DigestSign(mctx, NULL, &siglen, TEST_DATA, TEST_DATA_LEN) == 1 &&
           siglen == 256 &&
           (sig = OPENSSL_malloc(siglen)) != NULL &&
           EVP_DigestSign(mctx, sig, &siglen, TEST_DATA, TEST_DATA_LEN) == 1);

    /* 验签：PSS 参数下必须验过；同一份签名按 PKCS#1 v1.5 必须验不过。
     * 后半条是"这段签名确实出自 PSS"的反向证据 —— 只靠签名长度是分不开
     * 两种 padding 的，否则 PSS 实现整体缺失时本用例仍会 PASS。 */
    if (ok) {
        EVP_MD_CTX *vctx = EVP_MD_CTX_new();
        EVP_PKEY_CTX *vpctx = NULL;
        int pss_ok = 0;
        if (vctx != NULL &&
            EVP_DigestVerifyInit(vctx, &vpctx, EVP_sha256(), NULL, pkey) == 1 &&
            vpctx != NULL &&
            EVP_PKEY_CTX_set_rsa_padding(vpctx, RSA_PKCS1_PSS_PADDING) == 1 &&
            EVP_PKEY_CTX_set_rsa_pss_saltlen(vpctx, RSA_PSS_SALTLEN_DIGEST) == 1) {
            pss_ok = (EVP_DigestVerify(vctx, sig, siglen, TEST_DATA, TEST_DATA_LEN) == 1);
        }
        EVP_MD_CTX_free(vctx);

        vctx = EVP_MD_CTX_new();
        vpctx = NULL;
        int v15_ok = -1;
        if (vctx != NULL &&
            EVP_DigestVerifyInit(vctx, &vpctx, EVP_sha256(), NULL, pkey) == 1 &&
            vpctx != NULL &&
            EVP_PKEY_CTX_set_rsa_padding(vpctx, RSA_PKCS1_PADDING) == 1) {
            v15_ok = (EVP_DigestVerify(vctx, sig, siglen, TEST_DATA, TEST_DATA_LEN) == 1);
            ERR_clear_error();
        }
        EVP_MD_CTX_free(vctx);

        ok = pss_ok && (v15_ok == 0);
        if (!ok) {
            fprintf(stderr,
                    "    ERR RSA-2048-PSS verify: pss_ok=%d pkcs1_verify_rc=%d"
                    " (期望 pss_ok=1 且 pkcs1 验签失败)\n",
                    pss_ok, v15_ok);
        }
    }

    if (sig) OPENSSL_free(sig);
    EVP_MD_CTX_free(mctx);
    EVP_PKEY_free(pkey);
    if (!ok) fprintf(stderr, "    ERR RSA-2048-PSS sign+verify failed\n");
    return ok;
}

/* ------------------------------------------------------------------ *
 *  T7: 随机数生成
 * ------------------------------------------------------------------ */
static int test_rand_bytes(void) {
    unsigned char buf[32];
    if (RAND_bytes(buf, sizeof(buf)) != 1) {
        fprintf(stderr, "    ERR RAND_bytes failed\n");
        return 0;
    }
    int any = 0;
    for (int i = 0; i < 32; i++) if (buf[i]) { any = 1; break; }
    if (!any) { fprintf(stderr, "    ERR RAND_bytes all zero\n"); return 0; }
    return 1;
}

static int test_rand_priv_bytes(void) {
    unsigned char buf[32];
    if (RAND_priv_bytes(buf, sizeof(buf)) != 1) {
        fprintf(stderr, "    ERR RAND_priv_bytes failed\n");
        return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------ *
 *  T8: TLS / X.509 / 错误栈
 * ------------------------------------------------------------------ */
static int test_ssl_ctx(void) {
    const SSL_METHOD *m = TLS_client_method();
    if (!m) { fprintf(stderr, "    ERR TLS_method failed\n"); return 0; }
    SSL_CTX *ctx = SSL_CTX_new(m);
    if (!ctx) { fprintf(stderr, "    ERR SSL_CTX_new failed\n"); return 0; }
    int ok = (SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION) == 1 &&
               SSL_CTX_set_cipher_list(ctx, "DEFAULT") == 1 &&
               SSL_CTX_set_default_verify_paths(ctx) == 1);
    SSL_CTX_free(ctx);
    if (!ok) fprintf(stderr, "    ERR SSL_CTX config failed\n");
    return ok;
}

static int test_x509_self_signed(void) {
    EVP_PKEY *pkey = NULL;
    EVP_PKEY_CTX *kctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
    if (!kctx) return 0;
    int ok = (EVP_PKEY_keygen_init(kctx) == 1 &&
               EVP_PKEY_CTX_set_rsa_keygen_bits(kctx, 2048) == 1 &&
               EVP_PKEY_keygen(kctx, &pkey) == 1);
    EVP_PKEY_CTX_free(kctx);
    if (!ok) { fprintf(stderr, "    ERR X509 keygen failed\n"); return 0; }

    X509 *x = X509_new();
    if (!x) { EVP_PKEY_free(pkey); return 0; }

    ok = (X509_set_version(x, 2) == 1 &&
           ASN1_INTEGER_set(X509_get_serialNumber(x), 1) == 1 &&
           X509_gmtime_adj(X509_get_notBefore(x), 0) != NULL &&
           X509_gmtime_adj(X509_get_notAfter(x), 31536000L) != NULL &&
           X509_set_pubkey(x, pkey) == 1);

    if (ok) {
        X509_NAME *name = X509_get_subject_name(x);
        X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                                  (const unsigned char *)"HarmonyOS PC Test", -1, -1, 0);
        X509_set_issuer_name(x, name);
        ok = (X509_sign(x, pkey, EVP_sha256()) != 0 &&
               X509_verify(x, pkey) == 1);
    }

    X509_free(x);
    EVP_PKEY_free(pkey);
    if (!ok) fprintf(stderr, "    ERR X509 self-signed failed\n");
    return ok;
}

static int test_err_stack(void) {
    ERR_clear_error();
    /* 故意构造一个错误：使用未初始化的 EVP_PKEY 签名 */
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    if (!ctx) { fprintf(stderr, "    ERR no context\n"); return 0; }
    EVP_PKEY *null_key = NULL;
    int ret = EVP_DigestSignInit(ctx, NULL, EVP_sha256(), NULL, null_key);
    unsigned long err = ERR_get_error();
    EVP_MD_CTX_free(ctx);
    ERR_clear_error();

    if (ret == 1) { fprintf(stderr, "    ERR: expected failure\n"); return 0; }
    if (err == 0) { fprintf(stderr, "    ERR: error stack empty after expected failure\n"); return 0; }
    return 1;
}

/* ------------------------------------------------------------------ *
 *  主入口
 * ------------------------------------------------------------------ */
int main(void) {
    printf("=== OpenSSL 3.0.21 HarmonyOS PC 综合测试 ===\n");
    printf("[8 类 / 17 用例]\n\n");

    /* OpenSSL 3.x: 必须加载 default provider */
    if (OSSL_PROVIDER_load(NULL, "default") == NULL) {
        fprintf(stderr, "WARN: failed to load default provider\n");
    }
    if (OSSL_PROVIDER_load(NULL, "legacy") == NULL) {
        fprintf(stderr, "WARN: failed to load legacy provider\n");
    }

    OpenSSL_add_all_algorithms();
    ERR_load_crypto_strings();

    printf("[1/8] Hash 摘要\n");
    report(test_sha1(),    "SHA-1");
    report(test_sha256(),  "SHA-256");
    report(test_sha512(),  "SHA-512");

    printf("\n[2/8] HMAC\n");
    report(test_hmac_sha256(), "HMAC-SHA256");

    printf("\n[3/8] 对称加密\n");
    report(test_aes_128_cbc(), "AES-128-CBC roundtrip");
    report(test_aes_256_cbc(), "AES-256-CBC roundtrip");
    report(test_aes_256_gcm(), "AES-256-GCM roundtrip");

    printf("\n[4/8] 非对称加密 (RSA)\n");
    report(test_rsa_2048(), "RSA-2048 keygen");
    report(test_rsa_4096(), "RSA-4096 keygen");

    printf("\n[5/8] 椭圆曲线 (ECC)\n");
    report(test_ecdh_p256(), "ECDH-P256 key agreement");

    printf("\n[6/8] 数字签名\n");
    report(test_ecdsa_sign(),  "ECDSA-P256 sign");
    report(test_rsa_pss_sign(), "RSA-2048-PSS sign+verify");

    printf("\n[7/8] 随机数生成\n");
    report(test_rand_bytes(),      "RAND_bytes(32)");
    report(test_rand_priv_bytes(), "RAND_priv_bytes(32)");

    printf("\n[8/8] TLS / X.509 / 错误栈\n");
    report(test_ssl_ctx(),         "SSL_CTX create+configure");
    report(test_x509_self_signed(), "X.509 self-signed cert");
    report(test_err_stack(),       "ERR error stack");

    printf("\n=== 测试结果 ===\n");
    printf("通过: %d\n", g_passed);
    printf("失败: %d\n", g_failed);
    printf("合计: %d\n", g_passed + g_failed);

    EVP_cleanup();
    ERR_free_strings();

    if (g_failed > 0) {
        fprintf(stderr, "\nFAIL: %d test(s) failed\n", g_failed);
        return 1;
    }
    printf("\nAll tests passed.\n");
    return 0;
}
