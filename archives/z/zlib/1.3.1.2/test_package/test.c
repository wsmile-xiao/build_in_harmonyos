#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

int main(void) {
    /* Basic zlib smoke test: compress and decompress a string */
    const char *input = "Hello, zlib 1.3.1!";
    uLong src_len = strlen(input);
    uLong cmp_len = compressBound(src_len);
    unsigned char *compressed = malloc(cmp_len);
    unsigned char *decompressed = malloc(src_len + 1);

    if (!compressed || !decompressed) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    /* Compress */
    if (compress(compressed, &cmp_len, (const Bytef *)input, src_len) != Z_OK) {
        fprintf(stderr, "compress failed\n");
        return 1;
    }

    /* Decompress */
    uLong dec_len = src_len;
    if (uncompress(decompressed, &dec_len, compressed, cmp_len) != Z_OK) {
        fprintf(stderr, "uncompress failed\n");
        return 1;
    }

    decompressed[dec_len] = '\0';
    if (strcmp((const char *)decompressed, input) != 0) {
        fprintf(stderr, "round-trip mismatch\n");
        return 1;
    }

    printf("test zlib 1.3.1: OK (compress+uncompress round-trip succeeded)\n");

    free(compressed);
    free(decompressed);
    return 0;
}
