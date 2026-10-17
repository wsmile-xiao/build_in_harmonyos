// test_package/test_package.c — globus-gsi-proxy-ssl 6.6 consumer test (L1)
// 真实调用 globus-gsi-proxy-ssl 的 ASN.1 编解码 API（本库无 globus_module
// activate 语义，不套用 globus-gsi-openssl-error 的 activate/wrap 模板）：
// 构造 PROXYCERTINFO（path length + PROXYPOLICY 策略）→ i2d DER 编码 →
// d2i 解码 → 字段校验（path length / 策略字节 / 策略语言 OID）→ 解码结果
// 二次 DER 编码与首次编码逐字节比对，验证库链接与编解码功能可用；
// 任一步失败 return 1。
#include <proxycertinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/asn1.h>
#include <openssl/objects.h>

static const char POLICY_TEXT[] = "POLICYLANGUAGE POLICY";

int main(void) {
    int step = 0;
    int rc = 1;
    PROXYCERTINFO *pci = NULL;
    PROXYCERTINFO *decoded = NULL;
    PROXYPOLICY *policy = NULL;
    ASN1_OBJECT *lang = NULL;
    unsigned char *der = NULL;
    unsigned char *der2 = NULL;
    unsigned char *p = NULL;
    const unsigned char *q = NULL;
    unsigned char *got = NULL;
    int got_len = 0;
    char lang_txt[64];
    int der_len = 0, der2_len = 0;

    /* 1. 构造：语言 OID + PROXYPOLICY + PROXYCERTINFO(path length=10) */
    step = 1;
    lang = OBJ_txt2obj(ANY_LANGUAGE_OID, 1);
    policy = PROXYPOLICY_new();
    pci = PROXYCERTINFO_new();
    if (lang == NULL || policy == NULL || pci == NULL) {
        goto out;
    }

    step = 2;
    if (PROXYCERTINFO_set_path_length(pci, 10) != 1) {
        goto out;
    }

    step = 3;
    if (PROXYPOLICY_set_policy_language(policy, lang) != 1 ||
        PROXYPOLICY_set_policy(policy, (unsigned char *) POLICY_TEXT,
                               (int) (sizeof(POLICY_TEXT) - 1)) != 1 ||
        PROXYCERTINFO_set_policy(pci, policy) != 1) {
        goto out;
    }

    /* 2. i2d DER 编码（先探长度再编码，两次返回值必须一致） */
    step = 4;
    der_len = i2d_PROXYCERTINFO(pci, NULL);
    if (der_len <= 0) {
        goto out;
    }
    der = (unsigned char *) malloc((size_t) der_len);
    if (der == NULL) {
        goto out;
    }
    p = der;
    if (i2d_PROXYCERTINFO(pci, &p) != der_len) {
        goto out;
    }

    /* 3. d2i 解码 */
    step = 5;
    q = der;
    decoded = d2i_PROXYCERTINFO(NULL, &q, der_len);
    if (decoded == NULL) {
        goto out;
    }

    /* 4. 字段校验：path length / 策略字节 / 策略语言 OID */
    step = 6;
    if (PROXYCERTINFO_get_path_length(decoded) != 10) {
        goto out;
    }

    step = 7;
    got = PROXYPOLICY_get_policy(PROXYCERTINFO_get_policy(decoded), &got_len);
    if (got == NULL || got_len != (int) (sizeof(POLICY_TEXT) - 1) ||
        memcmp(got, POLICY_TEXT, (size_t) got_len) != 0) {
        goto out;
    }

    step = 8;
    memset(lang_txt, 0, sizeof(lang_txt));
    if (OBJ_obj2txt(lang_txt, (int) sizeof(lang_txt),
                    PROXYPOLICY_get_policy_language(
                        PROXYCERTINFO_get_policy(decoded)), 1) <= 0 ||
        strcmp(lang_txt, ANY_LANGUAGE_OID) != 0) {
        goto out;
    }

    /* 5. 解码结果二次编码必须与首次编码逐字节一致（DER 规范编码确定性） */
    step = 9;
    der2_len = i2d_PROXYCERTINFO(decoded, NULL);
    if (der2_len != der_len) {
        goto out;
    }
    der2 = (unsigned char *) malloc((size_t) der2_len);
    if (der2 == NULL) {
        goto out;
    }
    p = der2;
    if (i2d_PROXYCERTINFO(decoded, &p) != der2_len ||
        memcmp(der, der2, (size_t) der_len) != 0) {
        goto out;
    }

    printf("test globus-gsi-proxy-ssl 6.6: OK "
           "(der=%d bytes, path_length=%ld, policy='%s', lang=%s)\n",
           der_len, PROXYCERTINFO_get_path_length(decoded),
           POLICY_TEXT, lang_txt);
    rc = 0;

out:
    if (rc != 0) {
        fprintf(stderr, "test globus-gsi-proxy-ssl 6.6: FAIL (step %d)\n",
                step);
    }
    free(der2);
    free(der);
    free(got);
    PROXYCERTINFO_free(decoded);
    PROXYCERTINFO_free(pci);
    PROXYPOLICY_free(policy);
    ASN1_OBJECT_free(lang);
    return rc;
}
