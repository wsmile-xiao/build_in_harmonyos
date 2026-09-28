// test_gzip_hpp.cpp — Substantive consumer test for gzip-hpp 0.1.0
// (Conan L1) — verifies a downstream consumer can include the packaged
// headers, link zlib (propagated via cpp_info.requires) and call the real
// public gzip API: gzip::compress / gzip::decompress / gzip::is_compressed /
// gzip::Decompressor, with observable round-trip results.

#include <gzip/compress.hpp>
#include <gzip/decompress.hpp>
#include <gzip/utils.hpp>
#include <gzip/version.hpp>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

static int failures = 0;
#define CHECK(cond, label) do { \
    if (!(cond)) { std::fprintf(stderr, "FAIL: %s\n", label); failures++; } \
} while (0)

int main()
{
    const std::string data = "hello gzip-hpp consumer test data hello hello hello";

    // 1) not compressed before, compressed after
    CHECK(!gzip::is_compressed(data.data(), data.size()), "plain data not marked compressed");

    // 2) compress returns a non-empty gzip stream (magic 0x1f 0x8b)
    std::string compressed = gzip::compress(data.data(), data.size());
    CHECK(!compressed.empty(), "compress produced output");
    CHECK(compressed.size() >= 2 &&
              static_cast<uint8_t>(compressed[0]) == 0x1f &&
              static_cast<uint8_t>(compressed[1]) == 0x8b,
          "gzip magic bytes present");
    CHECK(gzip::is_compressed(compressed.data(), compressed.size()), "compressed data detected");

    // 3) round trip: decompress == original
    std::string decompressed = gzip::decompress(compressed.data(), compressed.size());
    CHECK(decompressed == data, "decompress round-trips to original data");

    // 4) explicit compression level round trip
    std::string c2 = gzip::compress(data.data(), data.size(), 6);
    std::string d2 = gzip::decompress(c2.data(), c2.size());
    CHECK(d2 == data, "level-6 compress/decompress round-trips");

    // 5) Decompressor with a limit: small payload below limit succeeds
    gzip::Decompressor decomp(1024 * 1024);
    std::string out;
    decomp.decompress(out, compressed.data(), compressed.size());
    CHECK(out == data, "Decompressor API round-trips to original data");

    // 6) version macro available
    CHECK(std::string(GZIP_VERSION_STRING) == "1.0.0", "GZIP_VERSION_STRING present and correct");

    if (failures == 0) {
        std::printf("PASS: gzip-hpp consumer 验证通过: compress/decompress/is_compressed/"
                    "Decompressor 公开 API 全部可用 (round-trip %zu bytes -> %zu bytes)\n",
                    data.size(), compressed.size());
        return 0;
    }
    return 1;
}
