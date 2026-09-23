#include <stdio.h>
#include <string.h>
#include <fastlz.h>

int main(void) {
    const char *src = "Hello, HarmonyOS! FastLZ compression round-trip test.";
    char compressed[512];
    char decompressed[512];

    int src_size = (int)strlen(src) + 1;
    int csize = fastlz_compress(src, src_size, compressed);
    if (csize <= 0) {
        printf("FAIL: fastlz_compress returned %d\n", csize);
        return 1;
    }

    int dsize = fastlz_decompress(compressed, csize, decompressed, sizeof(decompressed));
    if (dsize < 0) {
        printf("FAIL: fastlz_decompress returned %d\n", dsize);
        return 1;
    }

    if (dsize != src_size || memcmp(src, decompressed, (size_t)dsize) != 0) {
        printf("FAIL: round-trip mismatch (compress=%d decompress=%d)\n", csize, dsize);
        return 1;
    }

    printf("PASS: FastLZ compress=%d decompress=%d round-trip OK\n", csize, dsize);
    return 0;
}