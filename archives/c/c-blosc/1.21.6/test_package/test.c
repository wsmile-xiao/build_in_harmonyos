#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "blosc.h"

int main(void)
{
    int32_t source[1024];
    int32_t restored[1024];
    unsigned char compressed[sizeof(source) + BLOSC_MAX_OVERHEAD];

    for (int i = 0; i < 1024; ++i) {
        source[i] = (int32_t)((i % 17) - 8);
        restored[i] = 0;
    }

    blosc_init();
    blosc_set_nthreads(1);

    int compressed_size = blosc_compress(5, BLOSC_SHUFFLE, sizeof(source[0]),
                                         sizeof(source), source, compressed,
                                         sizeof(compressed));
    if (compressed_size <= 0) {
        fprintf(stderr, "blosc_compress failed: %d\n", compressed_size);
        blosc_destroy();
        return 1;
    }

    int decompressed_size = blosc_decompress(compressed, restored, sizeof(restored));
    if (decompressed_size != (int)sizeof(source)) {
        fprintf(stderr, "unexpected decompressed size: %d\n", decompressed_size);
        blosc_destroy();
        return 1;
    }

    if (memcmp(source, restored, sizeof(source)) != 0) {
        fprintf(stderr, "roundtrip data mismatch\n");
        blosc_destroy();
        return 1;
    }

    blosc_destroy();
    printf("c-blosc roundtrip: OK (%d bytes compressed)\n", compressed_size);
    return 0;
}
