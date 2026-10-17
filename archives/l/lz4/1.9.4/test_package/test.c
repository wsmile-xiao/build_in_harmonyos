#include <stdio.h>
#include <string.h>
#include <lz4.h>

int main(void) {
    const char *src = "Hello, HarmonyOS! LZ4 compression round-trip test.";
    char compressed[256];
    char decompressed[256];

    int src_size = (int)strlen(src);
    int csize = LZ4_compress_default(src, compressed, src_size, sizeof(compressed));
    if (csize <= 0) {
        printf("FAIL: LZ4_compress_default returned %d\n", csize);
        return 1;
    }

    int dsize = LZ4_decompress_safe(compressed, decompressed, csize, sizeof(decompressed));
    if (dsize < 0) {
        printf("FAIL: LZ4_decompress_safe returned %d\n", dsize);
        return 1;
    }

    decompressed[dsize] = '\0';
    if (strcmp(src, decompressed) != 0) {
        printf("FAIL: round-trip mismatch\n");
        return 1;
    }

    printf("PASS: LZ4 compress=%d decompress=%d round-trip OK\n", csize, dsize);
    return 0;
}
