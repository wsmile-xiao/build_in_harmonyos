/* test_package consumer for cjose 0.6.2.7.
 *
 * 覆盖真实公开 API（非 print-only）：
 * 1. cjose_version() 版本一致性
 * 2. base64url 编解码往返（RFC 4648 §5 向量）
 * 3. JOSE header set/get/release
 * 4. HS256 JWS 端到端：oct JWK import → sign → export →
 *    import → verify → 明文一致性
 *
 * 每步失败打印第一条错误并返回非零；全部通过打印
 * "CJOSE TEST PACKAGE OK" 并返回 0。
 */
#include <cjose/cjose.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 上游 check_jws.c 同款 HS256 oct JWK 测试向量 */
static const char *OCT_JWK
    = "{ \"kty\": \"oct\", "
      "\"k\": \"AyM1SysPpbyDfgZld3umj1qzKObwVMkoqQ-EstJQLr_T-1qS0gZH75aKtMN3Yj0iPS4hcgUuTwjAzZr1Z9CAow\" }";

static int g_failures = 0;

#define CHECK(cond, msg)                                     \
    do                                                       \
    {                                                        \
        if (!(cond))                                         \
        {                                                    \
            fprintf(stderr, "FAIL: %s\n", msg);              \
            g_failures++;                                    \
        }                                                    \
    } while (0)

static void test_version(void)
{
    const char *v = cjose_version();
    CHECK(NULL != v, "cjose_version returned NULL");
    CHECK(strcmp(v, "0.6.2.7") == 0, "cjose_version mismatch");
}

static void test_base64url_roundtrip(void)
{
    /* 向量与上游 test/check_base64.c test_cjose_base64url_encode 一致
     * (JOSE base64url: RFC 4648 §5 字母表 + RFC 7515 去填充) */
    const uint8_t raw[] = "hello there";
    const size_t raw_len = 11; /* 不含结尾 NUL */
    const char *expect = "aGVsbG8gdGhlcmU";
    cjose_err err;
    char *enc = NULL;
    size_t enc_len = 0;

    memset(&err, 0, sizeof(err));
    CHECK(cjose_base64url_encode(raw, raw_len, &enc, &enc_len, &err),
          "cjose_base64url_encode failed");
    if (enc)
    {
        CHECK(enc_len == strlen(expect) && strcmp(enc, expect) == 0,
              "base64url encoding mismatch");

        uint8_t *dec = NULL;
        size_t dec_len = 0;
        CHECK(cjose_base64url_decode(enc, enc_len, &dec, &dec_len, &err),
              "cjose_base64url_decode failed");
        if (dec)
        {
            CHECK(dec_len == raw_len && memcmp(dec, raw, raw_len) == 0,
                  "base64url roundtrip mismatch");
            cjose_get_dealloc()(dec);
        }
        cjose_get_dealloc()(enc);
    }
}

static void test_header_api(void)
{
    cjose_err err;
    memset(&err, 0, sizeof(err));
    cjose_header_t *hdr = cjose_header_new(&err);
    CHECK(NULL != hdr, "cjose_header_new failed");
    if (hdr)
    {
        CHECK(cjose_header_set(hdr, CJOSE_HDR_KID, "test-package-kid", &err),
              "cjose_header_set failed");
        const char *val = cjose_header_get(hdr, CJOSE_HDR_KID, &err);
        CHECK(NULL != val && strcmp(val, "test-package-kid") == 0,
              "cjose_header_get mismatch");
        cjose_header_release(hdr);
    }
}

static void test_jws_hs256_roundtrip(void)
{
    cjose_err err;
    memset(&err, 0, sizeof(err));

    cjose_jwk_t *jwk = cjose_jwk_import(OCT_JWK, strlen(OCT_JWK), &err);
    CHECK(NULL != jwk, "cjose_jwk_import failed");
    if (!jwk)
        return;

    cjose_header_t *hdr = cjose_header_new(&err);
    CHECK(NULL != hdr, "cjose_header_new failed");
    if (!hdr)
    {
        cjose_jwk_release(jwk);
        return;
    }
    CHECK(cjose_header_set(hdr, CJOSE_HDR_ALG, CJOSE_HDR_ALG_HS256, &err),
          "cjose_header_set ALG failed");

    const char *plain = "OpenHarmony PC test package for cjose";
    size_t plain_len = strlen(plain);

    cjose_jws_t *jws = cjose_jws_sign(jwk, hdr, (const uint8_t *)plain, plain_len, &err);
    CHECK(NULL != jws, "cjose_jws_sign failed");
    if (jws)
    {
        const char *compact = NULL;
        CHECK(cjose_jws_export(jws, &compact, &err), "cjose_jws_export failed");
        CHECK(NULL != compact && strstr(compact, ".") != NULL,
              "compact serialization invalid");

        cjose_jws_t *jws2 = cjose_jws_import(compact, strlen(compact), &err);
        CHECK(NULL != jws2, "cjose_jws_import failed");
        if (jws2)
        {
            CHECK(cjose_jws_verify(jws2, jwk, &err), "cjose_jws_verify failed");

            char *got = NULL;
            size_t got_len = 0;
            CHECK(cjose_jws_get_plaintext(jws2, (uint8_t **)&got, &got_len, &err),
                  "cjose_jws_get_plaintext failed");
            if (got)
            {
                CHECK(got_len == plain_len && strncmp(got, plain, plain_len) == 0,
                      "verified plaintext mismatch");
            }
            cjose_jws_release(jws2);
        }
        cjose_jws_release(jws);
    }
    cjose_header_release(hdr);
    cjose_jwk_release(jwk);
}

int main(void)
{
    test_version();
    test_base64url_roundtrip();
    test_header_api();
    test_jws_hs256_roundtrip();

    if (g_failures != 0)
    {
        fprintf(stderr, "test package failed with %d failure(s)\n", g_failures);
        return 1;
    }
    printf("CJOSE TEST PACKAGE OK (version %s)\n", cjose_version());
    return 0;
}
