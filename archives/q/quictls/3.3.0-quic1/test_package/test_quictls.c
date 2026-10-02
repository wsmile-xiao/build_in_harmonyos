/* quictls 3.3.0-quic1 Conan L1 test (test_package)
 *
 * 直接编译 + 运行，验证：
 *   1) 加密核心（SHA-256 / AES-256-GCM / EC P-256 / RAND / TLS1.3 / X509）
 *   2) QUIC-TLS provider API（BoringSSL 兼容，本配方启用的 QUIC 特性）：
 *      SSL_set_quic_method / SSL_is_quic / SSL_set_quic_transport_params /
 *      SSL_get_peer_quic_transport_params / SSL_quic_read_level /
 *      SSL_quic_write_level / SSL_quic_max_handshake_flight_len /
 *      SSL_process_quic_post_handshake
 *
 * 对被测包的实质依赖（R34）：若包未按 QUIC 特性构建，SSL_set_quic_method 等
 * 符号缺失会在链接期失败，不会通过空壳测试蒙混。
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <openssl/ssl.h>
#include <openssl/evp.h>
#include <openssl/err.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include <openssl/x509.h>

static int g_failures = 0;

#define CHECK(name, cond)                                              \
    do {                                                               \
        int _ok = !!(cond);                                            \
        printf("%s %s\n", _ok ? "PASS" : "FAIL", name);                \
        if (!_ok) {                                                    \
            printf("  -> assertion failed at line %d\n", __LINE__);    \
            g_failures++;                                              \
        }                                                              \
    } while (0)

/* QUIC-BoringSSL 回调：记录成功并返回 1（测试不做真实握手） */
static int cb_set_encryption_secrets(SSL *ssl, OSSL_ENCRYPTION_LEVEL level,
                                     const uint8_t *read_secret,
                                     const uint8_t *write_secret,
                                     size_t secret_len)
{
    (void)ssl; (void)level; (void)read_secret; (void)write_secret; (void)secret_len;
    return 1;
}
static int cb_add_handshake_data(SSL *ssl, OSSL_ENCRYPTION_LEVEL level,
                                 const uint8_t *data, size_t len)
{
    (void)ssl; (void)level; (void)data; (void)len;
    return 1;
}
static int cb_flush_flight(SSL *ssl) { (void)ssl; return 1; }
static int cb_send_alert(SSL *ssl, enum ssl_encryption_level_t level, uint8_t alert)
{ (void)ssl; (void)level; (void)alert; return 1; }

static void test_version(void)
{
    const char *ver = OpenSSL_version(OPENSSL_VERSION);
    printf("  version: %s\n", ver ? ver : "(null)");
    CHECK("T1 version string contains 3.3.0+quic",
          ver && strstr(ver, "3.3.0+quic") != NULL);
}

static void test_sha256(void)
{
    unsigned char md[SHA256_DIGEST_LENGTH];
    SHA256((const unsigned char *)"abc", 3, md);
    static const unsigned char expect[32] = {
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,
        0x5d,0xae,0x22,0x23,0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,
        0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad
    };
    CHECK("T2 SHA-256('abc') known vector", memcmp(md, expect, 32) == 0);
}

static void test_aes_gcm(void)
{
    int ok = 0;
    unsigned char key[32] = {0};
    unsigned char iv[12] = {1,2,3,4,5,6,7,8,9,10,11,12};
    unsigned char pt[16] = "quictls-gcm-test";
    unsigned char ct[64], out[64], tag[16]; /* 64 >= 16 + EVP_MAX_BLOCK_LENGTH(32) 安全上界（检视 P3-5：防 Update+Final 最坏写入越界） */
    EVP_CIPHER_CTX *cx = EVP_CIPHER_CTX_new();
    if (cx
        && EVP_EncryptInit_ex(cx, EVP_aes_256_gcm(), NULL, key, iv) == 1) {
        int el = 0, fl = 0;
        if (EVP_EncryptUpdate(cx, ct, &el, pt, 16) == 1
            && EVP_EncryptFinal_ex(cx, ct + el, &fl) == 1
            && el + fl == 16
            && EVP_CIPHER_CTX_ctrl(cx, EVP_CTRL_GCM_GET_TAG, 16, tag) == 1) {
            EVP_CIPHER_CTX_reset(cx);
            int dl = 0, fl2 = 0;
            if (EVP_DecryptInit_ex(cx, EVP_aes_256_gcm(), NULL, key, iv) == 1
                && EVP_DecryptUpdate(cx, out, &dl, ct, 16) == 1
                && EVP_CIPHER_CTX_ctrl(cx, EVP_CTRL_GCM_SET_TAG, 16, tag) == 1
                && EVP_DecryptFinal_ex(cx, out + dl, &fl2) == 1)
                ok = (dl + fl2 == 16 && memcmp(out, pt, 16) == 0);
        }
    }
    EVP_CIPHER_CTX_free(cx);
    CHECK("T3 AES-256-GCM round trip", ok);
}

static void test_ec_p256(void)
{
    int ok = 0;
    EVP_PKEY *pk = NULL;
    EVP_PKEY_CTX *kctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (kctx
        && EVP_PKEY_keygen_init(kctx) == 1
        && EVP_PKEY_CTX_set_ec_paramgen_curve_nid(kctx, NID_X9_62_prime256v1) == 1
        && EVP_PKEY_keygen(kctx, &pk) == 1 && pk) {
        unsigned char sig[128];
        size_t siglen = sizeof(sig);
        int signed_ok = 0, verify_ok = 0;
        EVP_MD_CTX *m = EVP_MD_CTX_new();
        if (m && EVP_DigestSignInit(m, NULL, EVP_sha256(), NULL, pk) == 1
            && EVP_DigestSign(m, sig, &siglen, (const unsigned char *)"quictls-ec-data", 15) == 1)
            signed_ok = 1;
        /* 签名态 MD_CTX 不能直接验签：reset 后重新 init 为验签态 */
        if (m) {
            EVP_MD_CTX_reset(m);
            if (EVP_DigestVerifyInit(m, NULL, EVP_sha256(), NULL, pk) == 1
                && EVP_DigestVerify(m, sig, siglen, (const unsigned char *)"quictls-ec-data", 15) == 1)
                verify_ok = 1;
        }
        EVP_MD_CTX_free(m);
        ok = signed_ok && verify_ok;
    }
    EVP_PKEY_CTX_free(kctx);
    EVP_PKEY_free(pk);
    CHECK("T4 EC P-256 keygen + sign/verify", ok);
}

static void test_rand(void)
{
    unsigned char buf[32] = {0};
    int ret = RAND_bytes(buf, 32);
    int nonzero = 0;
    for (int i = 0; i < 32; i++) if (buf[i]) { nonzero = 1; break; }
    CHECK("T5 RAND_bytes", ret == 1 && nonzero);
}

static void test_tls13(void)
{
    SSL_CTX *c = SSL_CTX_new(TLS_method());
    int ok = c && SSL_CTX_set_min_proto_version(c, TLS1_3_VERSION) == 1;
    SSL_CTX_free(c);
    CHECK("T6 TLS 1.3 context", ok);
}

static void test_x509(void)
{
    int ok = 0;
    EVP_PKEY *pk = EVP_PKEY_Q_keygen(NULL, NULL, "EC", "P-256");
    X509 *x = NULL;
    X509_NAME *nm = NULL;
    if (pk) {
        x = X509_new();
        nm = X509_NAME_new();
        if (x && nm
            && X509_NAME_add_entry_by_NID(nm, NID_commonName, MBSTRING_ASC,
                                          (const unsigned char *)"quictls-test", -1, -1, 0) == 1
            && X509_set_version(x, 3) == 1
            && ASN1_INTEGER_set(X509_get_serialNumber(x), 1) == 1
            && X509_set_subject_name(x, nm) == 1
            && X509_set_issuer_name(x, nm) == 1
            && X509_gmtime_adj(X509_getm_notBefore(x), 0) != NULL
            && X509_gmtime_adj(X509_getm_notAfter(x), 3600) != NULL
            && X509_set_pubkey(x, pk) == 1
            && X509_sign(x, pk, EVP_sha256()) > 0)
            ok = (X509_verify(x, pk) == 1);
    }
    X509_NAME_free(nm);
    X509_free(x);
    EVP_PKEY_free(pk);
    CHECK("T7 X509 self-signed cert + verify", ok);
}

static void test_quic(void)
{
    SSL_CTX *c = SSL_CTX_new(TLS_method());
    SSL *s = c ? SSL_new(c) : NULL;
    if (!s) {
        CHECK("T8 QUIC SSL setup", 0);
        SSL_CTX_free(c);
        return;
    }

    SSL_QUIC_METHOD m;
    memset(&m, 0, sizeof(m));
    m.set_encryption_secrets = cb_set_encryption_secrets;
    m.add_handshake_data = cb_add_handshake_data;
    m.flush_flight = cb_flush_flight;
    m.send_alert = cb_send_alert;

    CHECK("T8 SSL_set_quic_method", SSL_set_quic_method(s, &m) == 1);
    CHECK("T8b SSL_is_quic", SSL_is_quic(s) == 1);

    /* 本地 transport params（QUIC 传输参数扩展，握手时随 ClientHello 发出） */
    static const uint8_t tp[] = {
        0x00, 0x00, 0x00, 0x0a, 0x01, 0x00, 0x00, 0x00, 0x01
    };
    CHECK("T9 SSL_set_quic_transport_params",
          SSL_set_quic_transport_params(s, tp, sizeof(tp)) == 1);

    size_t plen = 0;
    const uint8_t *peer = NULL;
    SSL_get_peer_quic_transport_params(s, &peer, &plen);
    CHECK("T9b peer transport params absent pre-handshake", peer == NULL && plen == 0);

    CHECK("T10 read/write level = initial pre-handshake",
          SSL_quic_read_level(s) == ssl_encryption_initial
          && SSL_quic_write_level(s) == ssl_encryption_initial);

    size_t flight = SSL_quic_max_handshake_flight_len(s, ssl_encryption_initial);
    printf("  max handshake flight len(initial) = %zu\n", flight);
    /* 检视 P3-1：无符号 size_t 的 flight >= 0 恒真无区分力；
     * 改为断言"调用未破坏 SSL 状态"（pre-handshake 必须仍处于 init 态） */
    CHECK("T11 SSL_quic_max_handshake_flight_len, SSL still pre-handshake",
          SSL_is_init_finished(s) == 0);

    /* pre-handshake（SSL_in_init）时实现返回 0 并 raise
     * ERR_R_SHOULD_NOT_HAVE_BEEN_CALLED（ssl/ssl_quic.c:374）——断言该守卫语义 */
    CHECK("T12 SSL_process_quic_post_handshake pre-handshake == 0",
          SSL_process_quic_post_handshake(s) == 0);

    SSL_free(s);
    SSL_CTX_free(c);
}

int main(void)
{
    ERR_load_crypto_strings();
    printf("quictls 3.3.0-quic1 L1 test\n");
    test_version();
    test_sha256();
    test_aes_gcm();
    test_ec_p256();
    test_rand();
    test_tls13();
    test_x509();
    test_quic();

    if (g_failures) {
        printf("RESULT: FAIL (%d check(s) failed)\n", g_failures);
        return 1;
    }
    printf("RESULT: PASS\n");
    return 0;
}
