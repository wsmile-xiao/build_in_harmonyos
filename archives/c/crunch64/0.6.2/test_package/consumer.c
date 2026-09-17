#include <crunch64.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
typedef Crunch64Error (*bound_fn)(size_t *, size_t, const uint8_t *);
typedef Crunch64Error (*codec_fn)(size_t *, uint8_t *, size_t, const uint8_t *);

static int roundtrip(bound_fn cb, codec_fn c, bound_fn db, codec_fn d, const char *magic)
{
    uint8_t input[4097], output[4097];
    const size_t lengths[] = {1, 4, 31, 32, 33, 4096, 4097};
    for (size_t i = 0; i < sizeof(input); ++i) input[i] = (uint8_t)(i % 251);
    for (size_t i = 0; i < sizeof(lengths) / sizeof(lengths[0]); ++i) {
        size_t n = lengths[i], bound = 0, restored = 0;
        CHECK(cb(&bound, n, input) == Crunch64Error_Okay);
        CHECK(bound >= 16);
        uint8_t *packed = malloc(bound);
        CHECK(packed != NULL);
        size_t used = bound;
        Crunch64Error result = c(&used, packed, n, input);
        if (result != Crunch64Error_Okay || used > bound || memcmp(packed, magic, 4)) {
            fprintf(stderr, "format=%s input=%zu bound=%zu used=%zu error=%d\n", magic, n, bound, used, (int)result);
            free(packed); CHECK(0);
        }
        result = db(&restored, used, packed);
        if (result != Crunch64Error_Okay || restored != n) { free(packed); CHECK(0); }
        restored = sizeof(output);
        result = d(&restored, output, used, packed);
        free(packed);
        CHECK(result == Crunch64Error_Okay);
        CHECK(restored == n && memcmp(input, output, n) == 0);
    }
    return 0;
}

static int errors(void)
{
    const uint8_t invalid[16] = {0};
    size_t n = 0;
    CHECK(crunch64_yaz0_decompress_bound(&n, sizeof(invalid), invalid) == Crunch64Error_InvalidYaz0Header);
    CHECK(crunch64_yay0_decompress_bound(&n, sizeof(invalid), invalid) == Crunch64Error_InvalidYay0Header);
    CHECK(crunch64_mio0_decompress_bound(&n, sizeof(invalid), invalid) == Crunch64Error_InvalidMio0Header);
    CHECK(crunch64_yaz0_compress_bound(NULL, sizeof(invalid), invalid) == Crunch64Error_NullPointer);
    CHECK(crunch64_yay0_compress_bound(NULL, sizeof(invalid), invalid) == Crunch64Error_NullPointer);
    CHECK(crunch64_mio0_compress_bound(NULL, sizeof(invalid), invalid) == Crunch64Error_NullPointer);
    CHECK(crunch64_yay0_compress_bound(&n, SIZE_MAX, invalid) == Crunch64Error_OutOfBounds);
    CHECK(crunch64_mio0_compress_bound(&n, SIZE_MAX, invalid) == Crunch64Error_OutOfBounds);
    uint8_t dst[256];
    n = sizeof(dst);
    CHECK(crunch64_gzip_compress(&n, dst, sizeof(invalid), invalid, 3, false) == Crunch64Error_InvalidCompressionLevel);
    n = sizeof(dst);
    CHECK(crunch64_gzip_compress(&n, dst, sizeof(invalid), invalid, 10, false) == Crunch64Error_InvalidCompressionLevel);
    return 0;
}

static int gzip_footer(void)
{
    const uint8_t input[] = "123456789";
    /* RFC 1952 CRC32 test vector, followed by the little-endian input size. */
    const uint8_t footer[] = {0x26, 0x39, 0xf4, 0xcb, 9, 0, 0, 0};
    size_t bound = 0;
    CHECK(crunch64_gzip_compress_bound(&bound, 9, input) == Crunch64Error_Okay);
    uint8_t *packed = malloc(bound);
    CHECK(packed != NULL);
    for (int level = 4; level <= 9; ++level) {
        for (int small = 0; small <= 1; ++small) {
            size_t used = bound;
            Crunch64Error result = crunch64_gzip_compress(&used, packed, 9, input, level, small != 0);
            if (result != Crunch64Error_Okay || used < 8 || used > bound ||
                memcmp(packed + used - 8, footer, 8)) { free(packed); CHECK(0); }
        }
    }
    free(packed);
    return 0;
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    int result = 1;
    if (!strcmp(argv[1], "yaz0")) result = roundtrip(crunch64_yaz0_compress_bound, crunch64_yaz0_compress, crunch64_yaz0_decompress_bound, crunch64_yaz0_decompress, "Yaz0");
    else if (!strcmp(argv[1], "yay0")) result = roundtrip(crunch64_yay0_compress_bound, crunch64_yay0_compress, crunch64_yay0_decompress_bound, crunch64_yay0_decompress, "Yay0");
    else if (!strcmp(argv[1], "mio0")) result = roundtrip(crunch64_mio0_compress_bound, crunch64_mio0_compress, crunch64_mio0_decompress_bound, crunch64_mio0_decompress, "MIO0");
    else if (!strcmp(argv[1], "errors")) result = errors();
    else if (!strcmp(argv[1], "gzip")) result = gzip_footer();
    if (!result) printf("PASS crunch64 consumer %s\n", argv[1]);
    return result;
}
