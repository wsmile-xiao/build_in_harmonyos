#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

int main(void) {
    const char *input = "Hello, zlib 1.3.1.1.1!";
    uLong src_len = strlen(input);
    uLong compressed_len = compressBound(src_len);
    unsigned char *compressed = malloc(compressed_len);
    unsigned char *decompressed = malloc(src_len + 1);

    if (compressed == NULL || decompressed == NULL) {
        return 1;
    }

    if (compress(compressed, &compressed_len, (const Bytef *)input, src_len) != Z_OK) {
        return 2;
    }

    uLong decompressed_len = src_len;
    if (uncompress(decompressed, &decompressed_len, compressed, compressed_len) != Z_OK) {
        return 3;
    }

    decompressed[decompressed_len] = '\0';
    if (strcmp((const char *)decompressed, input) != 0) {
        return 4;
    }

    printf("zlib %s OK\n", zlibVersion());
    free(compressed);
    free(decompressed);
    return 0;
}
