#include <blosc2.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int check(int condition, const char *message) {
    if (!condition) { fprintf(stderr, "FAIL: %s\n", message); return 1; }
    printf("PASS: %s\n", message);
    return 0;
}

int main(void) {
    uint8_t source[1024], compressed[2048], restored[1024];
    int failures = 0;
    for (size_t i = 0; i < sizeof(source); ++i)
        source[i] = (uint8_t)((i * 37U) ^ (i >> 3));
    blosc2_init();
    int compressed_size = blosc2_compress(
        5, 1, 1, source, (int32_t)sizeof(source),
        compressed, (int32_t)sizeof(compressed));
    failures += check(compressed_size > 0, "compression returns a positive size");
    int restored_size = -1;
    if (compressed_size > 0)
        restored_size = blosc2_decompress(
            compressed, compressed_size, restored, (int32_t)sizeof(restored));
    failures += check(restored_size == (int)sizeof(source),
                      "decompression restores the original size");
    failures += check(restored_size == (int)sizeof(source) &&
                      memcmp(source, restored, sizeof(source)) == 0,
                      "round-trip data matches");
    const char *codec_name = NULL;
    int codec_rc = blosc2_compcode_to_compname(BLOSC_BLOSCLZ, &codec_name);
    failures += check(codec_rc == 0 && codec_name != NULL,
                      "codec name API returns a value");
    blosc2_destroy();
    if (failures != 0) return 1;
    printf("blosc2 3.2.3: all 4 assertions passed\n");
    return 0;
}

