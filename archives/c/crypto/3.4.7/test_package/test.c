/*
 * test_package 消费者测试 — crypto 3.4.7 (OpenSSL)
 *
 * R34: test 必须实质依赖被测包。本测试实际调用 OpenSSL 公开 API：
 *   - OPENSSL_version()           版本字符串
 *   - SSL_CTX_new(TLS_client_method)  SSL/TLS 上下文创建
 *   - EVP_Digest()                SHA-256 哈希（使用 EVP 接口）
 *   - RAND_bytes()                熵源（验证 E235 getrandom 种子路径可工作）
 */
#include <stdio.h>
#include <string.h>

#include <openssl/ssl.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/crypto.h>

int main(void) {
    int failures = 0;

    /* 1. 版本检查 */
    const char *ver = OpenSSL_version(OPENSSL_VERSION);
    printf("OpenSSL version: %s\n", ver);
    if (ver == NULL || strstr(ver, "3.4.7") == NULL) {
        fprintf(stderr, "FAIL: unexpected OpenSSL version\n");
        failures++;
    }

    /* 2. SSL_CTX 创建/释放（libssl 实质链接验证） */
    SSL_CTX *ctx = SSL_CTX_new(TLS_client_method());
    if (ctx == NULL) {
        fprintf(stderr, "FAIL: SSL_CTX_new returned NULL\n");
        failures++;
    } else {
        SSL_CTX_free(ctx);
    }

    /* 3. EVP_Digest SHA-256（libcrypto EVP 接口） */
    const unsigned char msg[] = "crypto-3.4.7 harmonyos test";
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    if (EVP_Digest(msg, sizeof(msg) - 1, digest, &digest_len,
                   EVP_sha256(), NULL) != 1) {
        fprintf(stderr, "FAIL: EVP_Digest failed\n");
        failures++;
    } else {
        printf("SHA-256 digest length: %u\n", digest_len);
    }

    /* 4. RAND_bytes（验证 getrandom 熵种子路径） */
    unsigned char rnd[16];
    if (RAND_bytes(rnd, sizeof(rnd)) != 1) {
        fprintf(stderr, "FAIL: RAND_bytes failed\n");
        failures++;
    } else {
        printf("RAND_bytes: ok\n");
    }

    if (failures != 0) {
        fprintf(stderr, "test_crypto: %d failure(s)\n", failures);
        return 1;
    }
    printf("test_crypto: all OpenSSL API checks passed\n");
    return 0;
}
