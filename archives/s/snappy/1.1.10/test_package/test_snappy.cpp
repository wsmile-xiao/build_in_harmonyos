/*
 * Snappy 1.1.10 consumer test — R34: actually call the snappy C++ API.
 *
 * Uses snappy::Compress / snappy::Uncompress (C++ API, snappy.h) plus the
 * C API (snappy-c.h) for a compression/decompression round-trip, verifying
 * the library works end to end on OHOS aarch64.
 */
#include <snappy.h>
#include <snappy-c.h>
#include <string>
#include <string.h>
#include <stdio.h>

int main(void) {
    /* --- Part 1: C++ API round-trip (snappy::Compress / snappy::Uncompress) --- */
    const std::string input =
        "Hello, Snappy! This is a test string for compression on OHOS aarch64. "
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

    std::string compressed;
    size_t compressed_len = snappy::Compress(input.data(), input.size(), &compressed);
    if (compressed_len == 0 || compressed_len != compressed.size()) {
        fprintf(stderr, "snappy::Compress failed: len=%zu\n", compressed_len);
        return 1;
    }

    std::string uncompressed;
    bool ok = snappy::Uncompress(compressed.data(), compressed.size(), &uncompressed);
    if (!ok) {
        fprintf(stderr, "snappy::Uncompress returned false\n");
        return 1;
    }
    if (uncompressed != input) {
        fprintf(stderr, "C++ API round-trip mismatch!\n");
        return 1;
    }
    printf("[C++ API] round-trip OK: %zu -> %zu -> %zu bytes\n",
           input.size(), compressed.size(), uncompressed.size());

    /* --- Part 2: GetUncompressedLength + MaxCompressedLength sanity --- */
    size_t ulen = 0;
    if (!snappy::GetUncompressedLength(compressed.data(), compressed.size(), &ulen)
        || ulen != input.size()) {
        fprintf(stderr, "GetUncompressedLength failed or mismatched: %zu vs %zu\n",
                ulen, input.size());
        return 1;
    }
    size_t max_len = snappy::MaxCompressedLength(input.size());
    if (max_len < compressed.size()) {
        fprintf(stderr, "MaxCompressedLength sanity failed\n");
        return 1;
    }
    printf("[C++ API] GetUncompressedLength=%zu, MaxCompressedLength=%zu OK\n",
           ulen, max_len);

    /* --- Part 3: C API round-trip (snappy-c.h) --- */
    const char* cinput = "C API round-trip test on OHOS.";
    size_t cinput_len = strlen(cinput);

    size_t cbuf_len = snappy_max_compressed_length(cinput_len);
    char cbuf[256];
    snappy_status rc = snappy_compress(cinput, cinput_len, cbuf, &cbuf_len);
    if (rc != SNAPPY_OK) {
        fprintf(stderr, "snappy_compress failed: %d\n", rc);
        return 1;
    }

    char dcbuf[256];
    size_t dcbuf_len = sizeof(dcbuf);
    rc = snappy_uncompress(cbuf, cbuf_len, dcbuf, &dcbuf_len);
    if (rc != SNAPPY_OK) {
        fprintf(stderr, "snappy_uncompress failed: %d\n", rc);
        return 1;
    }
    if (dcbuf_len != cinput_len || memcmp(dcbuf, cinput, cinput_len) != 0) {
        fprintf(stderr, "C API round-trip mismatch!\n");
        return 1;
    }
    printf("[C API] round-trip OK: %zu -> %zu -> %zu bytes\n",
           cinput_len, cbuf_len, dcbuf_len);

    printf("All snappy 1.1.10 tests passed.\n");
    return 0;
}
