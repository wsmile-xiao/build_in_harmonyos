#include <openssl/crypto.h>
#include <openssl/sha.h>
#include <openssl/ssl.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int passed = 0;
    const int total = 3;

    const char *version_text = OpenSSL_version(OPENSSL_VERSION);
    if (version_text && strstr(version_text, "1.1.1w") != NULL) {
        printf("[PASS] OpenSSL version: %s\n", version_text);
        passed++;
    } else {
        printf("[FAIL] OpenSSL version mismatch: %s\n",
               version_text ? version_text : "NULL");
    }

    const char *msg = "OpenHarmony OpenSSL 1.1.1w";
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256((const unsigned char *)msg, strlen(msg), hash);
    int nonzero = 0;
    for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i) {
        if (hash[i] != 0) {
            nonzero = 1;
            break;
        }
    }
    if (nonzero) {
        printf("[PASS] SHA256 computed\n");
        passed++;
    } else {
        printf("[FAIL] SHA256 output is all zeros\n");
    }

    SSL_library_init();
    SSL_CTX *ctx = SSL_CTX_new(TLS_method());
    if (ctx != NULL) {
        printf("[PASS] SSL_CTX created\n");
        SSL_CTX_free(ctx);
        passed++;
    } else {
        printf("[FAIL] SSL_CTX creation failed\n");
    }

    printf("openssl functional checks passed: %d/%d\n", passed, total);
    return passed == total ? 0 : 1;
}
