#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <sha256.h>

int main(void) {
    struct SHA256Context ctx;
    unsigned char hash[32];
    const unsigned char *test_input = (const unsigned char *)"The Cryptokit library - SHA-256 test";
    size_t test_len = strlen((const char *)test_input);
    int i;

    /* Initialize SHA-256 */
    SHA256_init(&ctx, 256);
    /* Feed data */
    SHA256_add_data(&ctx, (const unsigned char *)test_input, test_len);
    /* Finalize */
    SHA256_finish(&ctx, 256, hash);

    /* Print hash */
    printf("SHA-256(\"%s\") = ", (const char *)test_input);
    for (i = 0; i < 32; i++) {
        printf("%02hhx", hash[i]);
    }
    printf("\n");

    /* Verify against known-good SHA-256 digest */
    /* Pre-computed: SHA-256("The Cryptokit library - SHA-256 test") */
    const unsigned char expected[32] = {
        0x52, 0xa3, 0x99, 0x63, 0x08, 0x9a, 0xe9, 0xe2,
        0xa6, 0x9e, 0x00, 0x3f, 0x0d, 0x37, 0xe6, 0x9b,
        0xc0, 0xd8, 0x38, 0x1d, 0x71, 0x46, 0x0b, 0xcc,
        0xcd, 0xff, 0x66, 0x90, 0x59, 0x26, 0xed, 0x36
    };

    if (memcmp(hash, expected, 32) == 0) {
        printf("cryptokit SHA-256: digest MATCHES expected value ✅\n");
        return 0;
    } else {
        printf("cryptokit SHA-256: FAILED - digest mismatch!\n");
        printf("  Expected: ");
        for (i = 0; i < 32; i++) printf("%02hhx", expected[i]);
        printf("\n");
        return 1;
    }
}
