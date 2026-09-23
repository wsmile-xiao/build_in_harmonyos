#include <stdio.h>
#include <string.h>
#include <bzlib.h>

int main(void) {
    /* Verify library version */
    const char *version = BZ2_bzlibVersion();
    printf("bzip2 library version: %s\n", version);

    /* Round-trip compress + decompress test */
    const char *input = "bzip2 smoke test: hello from OHOS";
    int input_len = (int)strlen(input);
    char compressed[256];
    char decompressed[256];
    unsigned int comp_len = sizeof(compressed);
    unsigned int decompressed_len = sizeof(decompressed);
    int bzerror;

    /* Compress */
    bzerror = BZ2_bzBuffToBuffCompress(
        compressed, &comp_len, (char *)input, input_len, 9, 0, 0);
    if (bzerror != BZ_OK) {
        printf("FAIL: BZ2_bzBuffToBuffCompress returned %d\n", bzerror);
        return 1;
    }

    /* Decompress */
    bzerror = BZ2_bzBuffToBuffDecompress(
        decompressed, &decompressed_len, compressed, comp_len, 0, 0);
    if (bzerror != BZ_OK) {
        printf("FAIL: BZ2_bzBuffToBuffDecompress returned %d\n", bzerror);
        return 1;
    }

    /* Verify round-trip integrity */
    if (decompressed_len != input_len ||
        memcmp(input, decompressed, input_len) != 0) {
        printf("FAIL: decompressed content differs from original\n");
        return 1;
    }

    printf("PASS: bzip2 library API round-trip verified\n");
    return 0;
}
