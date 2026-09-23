#include <openssl/crypto.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include <openssl/ssl.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    static const unsigned char expected_digest[SHA256_DIGEST_LENGTH] = {
        0x42, 0xbd, 0xab, 0x88, 0x31, 0x1e, 0x40, 0xe0,
        0x71, 0x17, 0xb3, 0xc1, 0x59, 0x87, 0x5e, 0x42,
        0x3d, 0xd9, 0xd8, 0x32, 0x07, 0x0e, 0x1a, 0x4d,
        0x42, 0xbb, 0x38, 0x4f, 0x04, 0x0f, 0x63, 0x93,
    };
    unsigned char random_bytes[32] = {0};
    unsigned char digest[SHA256_DIGEST_LENGTH] = {0};
    SSL_CTX *context = NULL;
    const char *message = "OpenSSL OHOS consumer";

    if (strstr(OpenSSL_version(OPENSSL_VERSION), "4.0.1") == NULL)
        return 1;
    if (RAND_bytes(random_bytes, sizeof(random_bytes)) != 1)
        return 2;
    if (SHA256((const unsigned char *)message, strlen(message), digest) == NULL ||
        CRYPTO_memcmp(digest, expected_digest, sizeof(expected_digest)) != 0)
        return 3;

    context = SSL_CTX_new(TLS_method());
    if (context == NULL)
        return 4;
    SSL_CTX_free(context);

    printf("OpenSSL version, RAND, SHA256, and TLS context checks passed\n");
    return 0;
}
