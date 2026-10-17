#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "blosc2.h"

int main(void) {
    int32_t source[1024];
    int32_t restored[1024];
    unsigned char compressed[sizeof(source) + BLOSC2_MAX_OVERHEAD];

    for (int i = 0; i < 1024; ++i) {
        source[i] = (int32_t)((i % 17) - 8);
        restored[i] = 0;
    }

    blosc2_init();

    const char *ver = blosc2_get_version_string();
    printf("blosc2 version: %s\n", ver ? ver : "(null)");

    int csize = blosc2_compress(5, BLOSC_SHUFFLE, (int32_t)sizeof(source[0]),
                                source, (int32_t)sizeof(source), compressed,
                                (int32_t)sizeof(compressed));
    if (csize <= 0) {
        fprintf(stderr, "FAIL: blosc2_compress returned %d\n", csize);
        blosc2_destroy();
        return 1;
    }

    int dsize = blosc2_decompress(compressed, csize, restored,
                                  (int32_t)sizeof(restored));
    if (dsize != (int)sizeof(source)) {
        fprintf(stderr, "FAIL: blosc2_decompress returned %d (expected %zu)\n",
                dsize, sizeof(source));
        blosc2_destroy();
        return 1;
    }

    if (memcmp(source, restored, sizeof(source)) != 0) {
        fprintf(stderr, "FAIL: round-trip data mismatch\n");
        blosc2_destroy();
        return 1;
    }

    blosc2_destroy();
    printf("PASS: blosc2 round-trip OK (compressed %zu -> %d bytes)\n",
           sizeof(source), csize);
    return 0;
}
