#include <stdio.h>
#include <string.h>
#include <libbz3.h>

int main(void) {
    const char *version = bz3_version();
    if (!version || strlen(version) == 0) {
        fprintf(stderr, "FAIL: bz3_version() returned empty\n");
        return 1;
    }

    /* Test compress/decompress round-trip */
    const char *input = "Hello bzip3 on HarmonyOS! Compress and decompress test.";
    size_t in_size = strlen(input);
    size_t out_size = bz3_bound(in_size);
    uint8_t compressed[out_size];
    uint8_t decompressed[in_size + 1];

    int rc = bz3_compress(256 * 1024, (const uint8_t *)input, compressed, in_size, &out_size);
    if (rc != BZ3_OK) {
        fprintf(stderr, "FAIL: bz3_compress returned %d\n", rc);
        return 1;
    }

    size_t dec_size = in_size;
    rc = bz3_decompress(compressed, decompressed, out_size, &dec_size);
    if (rc != BZ3_OK) {
        fprintf(stderr, "FAIL: bz3_decompress returned %d\n", rc);
        return 1;
    }

    decompressed[dec_size] = '\0';
    if (strcmp((char *)decompressed, input) != 0) {
        fprintf(stderr, "FAIL: round-trip mismatch\n");
        return 1;
    }

    printf("OK: bzip3 %s compress/decompress round-trip\n", version);
    return 0;
}
