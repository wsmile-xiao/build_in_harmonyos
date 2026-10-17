#include <stdio.h>
#include <string.h>

#include <openssl/sha.h>
#include <openssl/ssl.h>
#include <tls.h>

static int
test_sha256(void)
{
    static const unsigned char expected[SHA256_DIGEST_LENGTH] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad,
    };
    unsigned char digest[SHA256_DIGEST_LENGTH];

    if (SHA256((const unsigned char *)"abc", 3, digest) == NULL)
        return 1;
    return memcmp(digest, expected, sizeof(expected)) == 0 ? 0 : 2;
}

static int
test_ssl_context(void)
{
    SSL_CTX *context = SSL_CTX_new(TLS_method());

    if (context == NULL)
        return 1;
    SSL_CTX_free(context);
    return 0;
}

static int
test_libtls_and_fault_injection(void)
{
    struct tls_config *config;
    const char *error;

    if (tls_init() != 0)
        return 1;
    config = tls_config_new();
    if (config == NULL)
        return 2;

    if (tls_config_set_ca_file(
            config, "/definitely/missing/libressl-test-ca.pem") == 0) {
        tls_config_free(config);
        return 3;
    }
    error = tls_config_error(config);
    if (error == NULL || error[0] == '\0') {
        tls_config_free(config);
        return 4;
    }

    tls_config_free(config);
    return 0;
}

int
main(void)
{
    int result;

    result = test_sha256();
    if (result != 0) {
        fprintf(stderr, "SHA-256 API test failed: %d\n", result);
        return 10 + result;
    }

    result = test_ssl_context();
    if (result != 0) {
        fprintf(stderr, "SSL context API test failed: %d\n", result);
        return 20 + result;
    }

    result = test_libtls_and_fault_injection();
    if (result != 0) {
        fprintf(stderr, "libtls fault-injection test failed: %d\n", result);
        return 30 + result;
    }

    puts("LibreSSL crypto, SSL, TLS, and negative-path checks passed");
    return 0;
}
