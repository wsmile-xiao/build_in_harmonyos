/*
 * jose_ohos_test.c — HarmonyOS PC 专项测试用例
 *
 * 通过库已安装/导出的公开头文件（<jose/jose.h> 及其子头）使用 jose：
 *   1. jose_jwk_gen 生成 ES256 椭圆曲线 JWK（RFC 7517）
 *   2. jose_jws_sig 用该 JWK 对 payload 签名（RFC 7515）
 *   3. jose_jws_ver 验证签名并断言结果（业务：JWT/JOSE 签名验证闭环）
 *   4. jose_jwk_thp 计算 JWK 指纹（RFC 7638）
 *   5. jose_b64_enc 输出 URL-safe Base64
 * 仅调用公开 API、公开头文件与正常链接目标，验证第三方使用者可编译、
 * 链接、调用并正常运行。使用 conan 安装产物（libjose.so.0 + libjansson）。
 */
#include <stdio.h>
#include <string.h>
#include <jansson.h>
#include <jose/jose.h>
#include <jose/b64.h>
#include <jose/jwk.h>
#include <jose/jws.h>

static int failures = 0;

static void check(int ok, const char *what)
{
    if (!ok) {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    } else {
        printf("PASS: %s\n", what);
    }
}

int main(void)
{
    /* 1. 生成 ES256 JWK */
    json_auto_t *jwk = json_pack("{s:s}", "alg", "ES256");
    check(jose_jwk_gen(NULL, jwk), "jose_jwk_gen(ES256)");
    check(json_string_value(json_object_get(jwk, "kty")) != NULL, "jwk has kty");
    check(json_string_value(json_object_get(jwk, "crv")) != NULL, "jwk has crv");

    /* 2. 对 payload 签名（JWS compact/hson 结构） */
    const char *payload = "HarmonyOS PC jose JWS round-trip";
    json_auto_t *jws = json_pack("{s:o}", "payload",
                                 jose_b64_enc(payload, strlen(payload)));
    check(jws != NULL, "jws object created");
    check(jose_jws_sig(NULL, jws, NULL, jwk), "jose_jws_sig(ES256)");
    /* 单签名时 jose 使用扁平结构：签名数据直接落在顶层 "signature" */
    check(json_object_get(jws, "signature") != NULL ||
          json_object_get(jws, "signatures") != NULL, "jws has signature data");

    /* 3. 验证签名 */
    check(jose_jws_ver(NULL, jws, NULL, jwk, true), "jose_jws_ver(ES256)");

    /* 3b. 篡改 payload 后验证必须失败（负向） */
    json_auto_t *bad = json_deep_copy(jws);
    if (bad) {
        json_t *p = json_object_get(bad, "payload");
        json_string_set(p, "bAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
        check(!jose_jws_ver(NULL, bad, NULL, jwk, true), "tampered jws rejected");
    }

    /* 4. JWK 指纹（RFC 7638, urlsafe b64 thumbprint） */
    json_auto_t *thp = jose_jwk_thp(NULL, jwk, "S256");
    check(thp != NULL, "jose_jwk_thp(S256)");
    if (thp && json_is_string(thp)) {
        const char *s = json_string_value(thp);
        printf("INFO: thumbprint len=%zu\n", s ? strlen(s) : 0);
        check(s != NULL && strlen(s) == 43, "thumbprint is 43 chars (sha256 urlsafe)");
    }

    /* 5. b64 URL-safe 往返 */
    const unsigned char raw[] = {0xde, 0xad, 0xbe, 0xef, 0x01, 0x02, 0x03};
    char enc[64] = {0};
    char dec[16] = {0};
    size_t enc_len = jose_b64_enc_buf(raw, sizeof(raw), enc, sizeof(enc));
    size_t dec_len = jose_b64_dec_buf(enc, enc_len, dec, sizeof(dec));
    check(enc_len > 0 && dec_len == sizeof(raw) && memcmp(dec, raw, sizeof(raw)) == 0,
          "b64 urlsafe round trip");

    /* 6. 公钥提取（jose_jwk_pub） */
    json_auto_t *pub = json_deep_copy(jwk);
    check(jose_jwk_pub(NULL, pub), "jose_jwk_pub");
    check(json_object_get(pub, "d") == NULL, "pub has no private part");

    if (failures == 0) {
        printf("ALL PASS: jose OHOS integration test\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}