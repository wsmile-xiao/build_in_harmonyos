#include <stdio.h>
#include <stdint.h>
#include <string.h>

/* Include aws-checksums API headers */
#include <aws/checksums/crc.h>
#include <aws/checksums/checksums.h>

/* Forward-declare aws-c-common types needed for init */
struct aws_allocator;
extern void aws_common_library_init(struct aws_allocator *allocator);

int main(void) {
    /* Initialize aws-c-common (required by aws-checksums) */
    aws_common_library_init((void *)0);

    /* Initialize aws-checksums library */
    aws_checksums_library_init((void *)0);

    /* Test CRC32: standard check value for "123456789" is 0xCBF43926 */
    const char *data = "123456789";
    size_t len = strlen(data);
    uint32_t crc = aws_checksums_crc32_ex((const uint8_t *)data, len, 0);
    printf("CRC32(\"123456789\") = 0x%08X (expected 0xCBF43926)\n", crc);
    if (crc != 0xCBF43926) {
        printf("FAIL: CRC32 mismatch\n");
        aws_checksums_library_clean_up();
        return 1;
    }

    /* Test CRC32C: standard check value for "123456789" is 0xE3069283 */
    uint32_t crc32c = aws_checksums_crc32c_ex((const uint8_t *)data, len, 0);
    printf("CRC32C(\"123456789\") = 0x%08X (expected 0xE3069283)\n", crc32c);
    if (crc32c != 0xE3069283) {
        printf("FAIL: CRC32C mismatch\n");
        aws_checksums_library_clean_up();
        return 1;
    }

    printf("All checksum tests passed: OK\n");
    aws_checksums_library_clean_up();
    return 0;
}
