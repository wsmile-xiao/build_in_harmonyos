#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <gmssl/sm3.h>
#include <gmssl/version.h>

int main(void) {
    /* Test 1: gmssl version */
    const char *ver = gmssl_version_str();
    if (ver == NULL) {
        fprintf(stderr, "FAIL: gmssl_version_str() returned NULL\n");
        return 1;
    }
    printf("gmssl version: %s\n", ver);

    /* Test 2: SM3 digest of "abc" */
    const uint8_t data[] = "abc";
    uint8_t dgst[SM3_DIGEST_SIZE];
    sm3_digest(data, 3, dgst);

    /* Expected SM3("abc") = 66c7f0f4 62eeedd9 d1f2d46b dc10e4e2 4167c487 5cf2f7a2 297da02b 8f4ba8e0 */
    const uint8_t expected[SM3_DIGEST_SIZE] = {
        0x66, 0xc7, 0xf0, 0xf4, 0x62, 0xee, 0xed, 0xd9,
        0xd1, 0xf2, 0xd4, 0x6b, 0xdc, 0x10, 0xe4, 0xe2,
        0x41, 0x67, 0xc4, 0x87, 0x5c, 0xf2, 0xf7, 0xa2,
        0x29, 0x7d, 0xa0, 0x2b, 0x8f, 0x4b, 0xa8, 0xe0
    };

    if (memcmp(dgst, expected, SM3_DIGEST_SIZE) != 0) {
        fprintf(stderr, "FAIL: SM3 digest mismatch\n");
        fprintf(stderr, "  got: ");
        for (int i = 0; i < SM3_DIGEST_SIZE; i++)
            fprintf(stderr, "%02x", dgst[i]);
        fprintf(stderr, "\n");
        return 1;
    }

    printf("SM3(\"abc\") = ");
    for (int i = 0; i < SM3_DIGEST_SIZE; i++)
        printf("%02x", dgst[i]);
    printf("\n");
    printf("test gmssl 3.1.1: OK\n");
    return 0;
}
