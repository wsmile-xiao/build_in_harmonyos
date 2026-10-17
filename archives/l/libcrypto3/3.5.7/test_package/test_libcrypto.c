#include <stdio.h>
#include <string.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/sha.h>
#include <openssl/rand.h>

int main(void) {
    int rc = 0;

    /* Test 1: SHA-256 digest */
    unsigned char data[] = "Hello, libcrypto3!";
    unsigned char md[SHA256_DIGEST_LENGTH];
    unsigned int md_len = 0;
    if (EVP_Digest(data, strlen((char*)data), md, &md_len, EVP_sha256(), NULL)) {
        printf("Test 1 (SHA-256): PASS (%u bytes)\n", md_len);
    } else {
        printf("Test 1 (SHA-256): FAIL\n");
        rc = 1;
    }

    /* Test 2: HMAC-SHA256 */
    unsigned char key[] = "secret-key";
    unsigned char hmac_result[EVP_MAX_MD_SIZE];
    unsigned int hmac_len = 0;
    HMAC(EVP_sha256(), key, strlen((char*)key), data, strlen((char*)data), hmac_result, &hmac_len);
    if (hmac_len > 0) {
        printf("Test 2 (HMAC-SHA256): PASS (%u bytes)\n", hmac_len);
    } else {
        printf("Test 2 (HMAC-SHA256): FAIL\n");
        rc = 1;
    }

    /* Test 3: AES-256-CBC encrypt */
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (ctx) {
        unsigned char aes_key[32];
        unsigned char aes_iv[16];
        RAND_bytes(aes_key, sizeof(aes_key));
        RAND_bytes(aes_iv, sizeof(aes_iv));

        if (EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, aes_key, aes_iv)) {
            unsigned char ciphertext[64];
            int outlen = 0;
            if (EVP_EncryptUpdate(ctx, ciphertext, &outlen, data, strlen((char*)data) + 1)) {
                int finallen = 0;
                EVP_EncryptFinal_ex(ctx, ciphertext + outlen, &finallen);
                outlen += finallen;
                printf("Test 3 (AES-256-CBC): PASS (%d bytes encrypted)\n", outlen);
            } else {
                printf("Test 3 (AES-256-CBC): FAIL (EncryptUpdate)\n");
                rc = 1;
            }
        } else {
            printf("Test 3 (AES-256-CBC): FAIL (EncryptInit)\n");
            rc = 1;
        }
        EVP_CIPHER_CTX_free(ctx);
    } else {
        printf("Test 3 (AES-256-CBC): FAIL (CTX_new)\n");
        rc = 1;
    }

    /* Test 4: RAND_bytes (random number generation) */
    unsigned char rand_buf[16];
    if (RAND_bytes(rand_buf, sizeof(rand_buf)) == 1) {
        printf("Test 4 (RAND_bytes): PASS\n");
    } else {
        printf("Test 4 (RAND_bytes): FAIL\n");
        rc = 1;
    }

    /* Test 5: OpenSSL version check — assert version matches expected */
    {
        unsigned long ver = OpenSSL_version_num();
        /* OPENSSL_VERSION_NUMBER format: MAJOR<<28 | MINOR<<20 | FIX<<12 | PATCH<<4 | STATUS
         * OpenSSL 3.5.7 => 3<<28 | 5<<20 | 0<<12 | 7<<4 | 0 = 0x30500070 */
        unsigned long expected = 0x30500070UL;
        if (ver == expected) {
            printf("Test 5 (Version): PASS (%s)\n", OpenSSL_version(OPENSSL_VERSION));
        } else {
            printf("Test 5 (Version): FAIL (got 0x%lx, expected 0x%lx)\n",
                   ver, expected);
            rc = 1;
        }
    }

    if (rc == 0) {
        printf("\nAll libcrypto3 tests PASSED\n");
    } else {
        printf("\nSome tests FAILED\n");
    }
    return rc;
}
