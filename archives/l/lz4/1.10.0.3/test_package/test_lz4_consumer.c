/* lz4 1.10.0.1 consumer cases (Path B):
 *  1) LZ4 frame API round-trip (lz4frame.h, streaming decompression context)
 *  2) dictionary compression round-trip via LZ4_loadDictSlow() -- the symbol
 *     officially promoted to stable in upstream v1.10.0
 * ASCII-only comments (MSVC CP936 safety, same rule as test.c).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lz4.h>
#include <lz4frame.h>

static int g_fails = 0;
#define CHECK(cond, msg) do { if (!(cond)) { \
    printf("FAIL: %s\n", msg); g_fails++; } } while (0)

static void fill_pattern(char *buf, size_t n, unsigned seed)
{
    unsigned x = seed;
    size_t i;
    for (i = 0; i < n; i++) {
        x = x * 1103515245u + 12345u;
        buf[i] = (char)('a' + (x >> 16) % 26);
    }
}

/* Case 1: LZ4F frame API compress/decompress round-trip */
static void test_frame_roundtrip(void)
{
    enum { SRC_LEN = 4096 };
    char src[SRC_LEN];
    size_t cap, csize, dsize, consumed;
    char *compressed;
    char decompressed[SRC_LEN];
    LZ4F_dctx *dctx = NULL;

    fill_pattern(src, sizeof(src), 1u);
    cap = LZ4F_compressFrameBound(sizeof(src), NULL);
    compressed = (char *)malloc(cap);
    CHECK(compressed != NULL, "malloc compressed buffer");

    csize = LZ4F_compressFrame(compressed, cap, src, sizeof(src), NULL);
    CHECK(!LZ4F_isError(csize), "LZ4F_compressFrame no error");
    CHECK(csize > 0 && csize < cap, "frame compressed within bound");
    printf("frame: %d -> %d bytes\n", (int)sizeof(src), (int)csize);

    CHECK(LZ4F_createDecompressionContext(&dctx, LZ4F_VERSION) == 0,
          "LZ4F_createDecompressionContext");
    dsize = sizeof(decompressed);
    consumed = csize;
    {
        size_t ret = LZ4F_decompress(dctx, decompressed, &dsize,
                                     compressed, &consumed, NULL);
        CHECK(!LZ4F_isError(ret), "LZ4F_decompress no error");
        CHECK(ret == 0, "frame fully decompressed in one pass");
        CHECK(consumed == csize, "all compressed input consumed");
    }
    CHECK(dsize == sizeof(src), "decompressed length matches");
    CHECK(memcmp(decompressed, src, sizeof(src)) == 0, "frame round-trip content");
    LZ4F_freeDecompressionContext(dctx);
    free(compressed);
}

/* Case 2: dictionary compression (stable since v1.10.0, LZ4_loadDictSlow) */
static void test_dictionary_roundtrip(void)
{
    enum { DICT_LEN = 2048, PAYLOAD_LEN = 512 };
    char dict[DICT_LEN];
    char payload[PAYLOAD_LEN];
    char compressed[LZ4_compressBound(PAYLOAD_LEN)];
    char restored[PAYLOAD_LEN];
    LZ4_stream_t *cctx;
    int csize, dsize;

    /* payload reuses the dictionary pattern so the dict actually helps */
    fill_pattern(dict, sizeof(dict), 7u);
    memcpy(payload, dict + 512, PAYLOAD_LEN);

    cctx = LZ4_createStream();
    CHECK(cctx != NULL, "LZ4_createStream");
    CHECK(LZ4_loadDictSlow(cctx, dict, sizeof(dict)) == (int)sizeof(dict),
          "LZ4_loadDictSlow loaded full dict (v1.10.0 stable symbol)");
    csize = LZ4_compress_fast_continue(cctx, payload, compressed,
                                       PAYLOAD_LEN, sizeof(compressed), 1);
    CHECK(csize > 0, "dict compression succeeded");
    LZ4_freeStream(cctx);
    printf("dict: %d -> %d bytes\n", PAYLOAD_LEN, csize);

    dsize = LZ4_decompress_safe_usingDict(compressed, restored, csize,
                                          PAYLOAD_LEN, dict, sizeof(dict));
    CHECK(dsize == PAYLOAD_LEN, "dict decompression length");
    CHECK(memcmp(restored, payload, PAYLOAD_LEN) == 0,
          "dictionary round-trip content");
}

int main(void)
{
    test_frame_roundtrip();
    test_dictionary_roundtrip();
    if (g_fails == 0) {
        printf("PASS: consumer cases frame-API + dictionary-API all OK\n");
        return 0;
    }
    printf("FAIL: %d consumer assertion(s) failed\n", g_fails);
    return 1;
}
