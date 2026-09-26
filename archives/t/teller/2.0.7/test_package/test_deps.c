/*
 * Dependency functional test for teller 2.0.7.
 *
 * teller 通过 rustify(default-tls) → reqwest → native-tls → openssl-sys
 * 使用 openssl/3.5.8.1；该依赖在 teller 产物中是**静态链接**（产物
 * DT_NEEDED 仅 libc.so），因此仅运行 teller 无法证明 OpenSSL 在 HarmonyOS
 * 上真实可用。本程序以消费者身份用 OHOS clang 编译并链接 openssl 包，
 * 在设备上实际执行 OpenSSL 代码路径。
 */
#include <stdio.h>
#include <string.h>

#include <openssl/bn.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/sha.h>

static int passed = 0;
static int failed = 0;

static void check(const char *name, int ok, const char *detail)
{
    if (ok) {
        passed++;
        printf("[ok] %s%s%s\n", name, detail ? ": " : "", detail ? detail : "");
    } else {
        failed++;
        fprintf(stderr, "[fail] %s%s%s\n", name, detail ? ": " : "",
                detail ? detail : "");
    }
}

/* SHA256("abc") 的已知摘要 */
static const unsigned char SHA256_ABC[32] = {
    0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
    0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
    0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
    0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
};

int main(void)
{
    char detail[256];

    /* 1. 版本信息 */
    const char *ver = OpenSSL_version(OPENSSL_VERSION);
    check("1: OpenSSL_version(OPENSSL_VERSION) 返回非空",
          ver != NULL && strstr(ver, "OpenSSL") != NULL, ver);

    unsigned long num = OpenSSL_version_num();
    snprintf(detail, sizeof(detail), "num=0x%lx", num);
    check("2: OpenSSL_version_num() >= 3.0.0", num >= 0x30000000UL, detail);

    /* 3. 一次性 SHA256 */
    unsigned char digest[SHA256_DIGEST_LENGTH];
    memset(digest, 0, sizeof(digest));
    SHA256((const unsigned char *)"abc", 3, digest);
    check("3: SHA256(\"abc\") 与已知摘要字节级一致",
          memcmp(digest, SHA256_ABC, sizeof(SHA256_ABC)) == 0, NULL);

    /* 4. EVP 摘要（provider 路径） */
    unsigned char digest2[SHA256_DIGEST_LENGTH];
    unsigned int digest2_len = 0;
    memset(digest2, 0, sizeof(digest2));
    int rc4 = EVP_Digest("abc", 3, digest2, &digest2_len, EVP_sha256(), NULL);
    snprintf(detail, sizeof(detail), "rc=%d len=%u", rc4, digest2_len);
    check("4: EVP_Digest(EVP_sha256) 与已知摘要一致",
          rc4 == 1 && digest2_len == 32 &&
          memcmp(digest2, SHA256_ABC, sizeof(SHA256_ABC)) == 0, detail);

    /* 5. CSPRNG */
    unsigned char rnd[32];
    memset(rnd, 0, sizeof(rnd));
    int rc5 = RAND_bytes(rnd, (int)sizeof(rnd));
    int nonzero = 0;
    for (size_t i = 0; i < sizeof(rnd); i++) {
        if (rnd[i] != 0) {
            nonzero = 1;
            break;
        }
    }
    snprintf(detail, sizeof(detail), "rc=%d nonzero=%d", rc5, nonzero);
    check("5: RAND_bytes(32) 成功且输出非全零", rc5 == 1 && nonzero, detail);

    /* 6. BIGNUM */
    BIGNUM *bn = BN_new();
    int rc6 = bn != NULL && BN_set_word(bn, 12345) == 1;
    char *hex = rc6 ? BN_bn2hex(bn) : NULL;
    check("6: BN_set_word(12345) → hex \"3039\"",
          hex != NULL && strcmp(hex, "3039") == 0, hex);
    if (hex != NULL) {
        OPENSSL_free(hex);
    }
    BN_free(bn);

    /* 7. AES-128-CBC 加解密往返（EVP cipher 路径，vault/aws provider 的 TLS 基础） */
    static const unsigned char key[16] = "0123456789abcdef";
    static const unsigned char iv[16] = "fedcba9876543210";
    const char *plain = "teller-openssl-harmonyos-roundtrip";
    unsigned char ct[128];
    unsigned char pt[128];
    int len = 0, ctlen = 0, ptlen = 0;
    memset(ct, 0, sizeof(ct));
    memset(pt, 0, sizeof(pt));

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    int ok7 = ctx != NULL;
    if (ok7) {
        ok7 = EVP_EncryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, key, iv) == 1;
        ok7 = ok7 && EVP_EncryptUpdate(ctx, ct, &len,
                                       (const unsigned char *)plain,
                                       (int)strlen(plain)) == 1;
        ctlen = len;
        ok7 = ok7 && EVP_EncryptFinal_ex(ctx, ct + ctlen, &len) == 1;
        ctlen += len;
        EVP_CIPHER_CTX_free(ctx);
    }
    ctx = EVP_CIPHER_CTX_new();
    if (ok7 && ctx != NULL) {
        ok7 = EVP_DecryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, key, iv) == 1;
        ok7 = ok7 && EVP_DecryptUpdate(ctx, pt, &len, ct, ctlen) == 1;
        ptlen = len;
        ok7 = ok7 && EVP_DecryptFinal_ex(ctx, pt + ptlen, &len) == 1;
        ptlen += len;
    }
    if (ctx != NULL) {
        EVP_CIPHER_CTX_free(ctx);
    }
    int roundtrip = ok7 && ptlen == (int)strlen(plain) &&
                    memcmp(pt, plain, (size_t)ptlen) == 0;
    /* PKCS#7 填充后密文长度 = 向上取整到 16 字节块 */
    int expected_ct = (int)((strlen(plain) / 16 + 1) * 16);
    snprintf(detail, sizeof(detail), "ct=%d pt=%d expect_ct=%d",
             ctlen, ptlen, expected_ct);
    check("7: AES-128-CBC 加密/解密往返一致（ct 长度 = PKCS#7 填充块）",
          roundtrip && ctlen == expected_ct, detail);

    printf("SUMMARY: executed=%d passed=%d failed=%d\n",
           passed + failed, passed, failed);
    if (failed) {
        return 1;
    }
    printf("openssl dependency test OK (tell 2.0.7 依赖在 HarmonyOS 上功能可用)\n");
    return 0;
}
