// test_package/test_package.c — globus-gsi-openssl-error 4.4 consumer test (L1)
// 真实调用 globus-gsi-openssl-error API：activate → 压入一个 OpenSSL 错误
// → globus_error_wrap_openssl_error 包装 → 打印顶层与 cause 链消息 →
// free → deactivate，验证库链接与包装功能可用；任一步失败 return 1。
#include <globus_error_openssl.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    globus_result_t rc;
    globus_object_t *err = NULL;
    globus_object_t *cause = NULL;
    const char *msg = NULL;
    const char *ossl_msg = NULL;

    /* 1. 激活模块 */
    rc = globus_module_activate(GLOBUS_GSI_OPENSSL_ERROR_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-gsi-openssl-error 4.4: FAIL "
                "(activate rc=%lu)\n", (unsigned long)rc);
        return 1;
    }

    /* 2. 向 OpenSSL 错误队列压入一个真实条目（通用内部错误；
       OpenSSL 3.x 已移除 ASN1 函数码/原因码宏，用 USER+INTERNAL_ERROR
       保证 1.1/3.x 双兼容） */
    ERR_put_error(ERR_LIB_USER, 0, ERR_R_INTERNAL_ERROR,
                  __FILE__, __LINE__);

    /* 3. wrap 为 globus 错误对象 */
    err = globus_error_wrap_openssl_error(
        GLOBUS_GSI_OPENSSL_ERROR_MODULE,
        42,
        __FILE__, "test_package", __LINE__,
        "wrap test");
    if (err == NULL) {
        fprintf(stderr, "test globus-gsi-openssl-error 4.4: FAIL "
                "(wrap returned NULL)\n");
        globus_module_deactivate(GLOBUS_GSI_OPENSSL_ERROR_MODULE);
        return 1;
    }

    /* 4. 顶层消息可打印 */
    msg = globus_object_printable_to_string(err);
    if (msg == NULL) {
        fprintf(stderr, "test globus-gsi-openssl-error 4.4: FAIL "
                "(printable_to_string NULL)\n");
        globus_object_free(err);
        globus_module_deactivate(GLOBUS_GSI_OPENSSL_ERROR_MODULE);
        return 1;
    }

    /* 5. cause 链携带 OpenSSL 错误层（"OpenSSL Error: ..." 文本） */
    cause = globus_error_base_get_cause(err);
    ossl_msg = cause ? globus_object_printable_to_string(cause) : NULL;
    if (ossl_msg == NULL || strstr(ossl_msg, "OpenSSL Error") == NULL) {
        fprintf(stderr, "test globus-gsi-openssl-error 4.4: FAIL "
                "(no OpenSSL Error cause, got: %s)\n",
                ossl_msg ? ossl_msg : "(null)");
        globus_object_free(err);
        globus_module_deactivate(GLOBUS_GSI_OPENSSL_ERROR_MODULE);
        return 1;
    }

    printf("test globus-gsi-openssl-error 4.4: OK "
           "(top=%s | cause=%s)\n", msg, ossl_msg);
    globus_object_free(err);

    /* 6. 反激活模块 */
    rc = globus_module_deactivate(GLOBUS_GSI_OPENSSL_ERROR_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-gsi-openssl-error 4.4: FAIL "
                "(deactivate rc=%lu)\n", (unsigned long)rc);
        return 1;
    }

    return 0;
}
