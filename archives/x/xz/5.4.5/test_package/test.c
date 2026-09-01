#include <stdio.h>
#include <stdlib.h>
#include <lzma.h>

int main(void) {
    /* R34: Real API check — verify liblzma is functional */
    if (lzma_version_string() == NULL) {
        fprintf(stderr, "FAIL: lzma_version_string() returned NULL\n");
        return 1;
    }
    printf("lzma version: %s\n", lzma_version_string());

    /* Test basic CRC32 computation (core liblzma API) */
    uint32_t crc = lzma_crc32((const uint8_t *)"hello", 5, 0);
    if (crc == 0) {
        fprintf(stderr, "FAIL: lzma_crc32 returned 0\n");
        return 1;
    }
    printf("lzma_crc32('hello') = 0x%08x\n", crc);
    printf("test xz 5.4.5: OK\n");
    return 0;
}
