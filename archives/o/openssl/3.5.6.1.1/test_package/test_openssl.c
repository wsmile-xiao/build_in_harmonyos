/*
 * test_openssl.c — OpenSSL 3.5.6 L1 test
 * Verifies: version string, SHA256 hashing, SSL library init
 */
#include <stdio.h>
#include <string.h>
#include <openssl/ssl.h>
#include <openssl/sha.h>
#include <openssl/crypto.h>

int main(void) {
    int passed = 0;
    int total = 3;

    /* Test 1: Version check */
    unsigned long version = OpenSSL_version_num();
    const char *version_text = OpenSSL_version(OPENSSL_VERSION);
    if (version_text && strstr(version_text, "3.5.6") != NULL) {
        printf("[PASS] OpenSSL version: %s (0x%lx)\n", version_text, version);
        passed++;
    } else {
        printf("[FAIL] OpenSSL version mismatch: %s\n", version_text ? version_text : "NULL");
    }

    /* Test 2: SHA256 hash computation */
    const char *msg = "Hello, OpenSSL!";
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256((const unsigned char *)msg, strlen(msg), hash);
    /* Verify hash is non-zero (basic sanity) */
    int nonzero = 0;
    for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        if (hash[i] != 0) { nonzero = 1; break; }
    }
    if (nonzero) {
        printf("[PASS] SHA256 hash computed for \"%s\"\n", msg);
        passed++;
    } else {
        printf("[FAIL] SHA256 hash is all zeros\n");
    }

    /* Test 3: SSL library initialization */
    SSL_library_init();
    SSL_CTX *ctx = SSL_CTX_new(TLS_method());
    if (ctx != NULL) {
        printf("[PASS] SSL_CTX created successfully\n");
        SSL_CTX_free(ctx);
        passed++;
    } else {
        printf("[FAIL] SSL_CTX creation failed\n");
    }

    printf("\nResults: %d/%d tests passed\n", passed, total);
    return (passed == total) ? 0 : 1;
}
