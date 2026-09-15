// test_metrohash.cpp — Substantive consumer test for metrohash 1.1.3 (Conan L1).
// Verifies a downstream consumer can link the packaged library and that the
// implementation reproduces the official verification vectors shipped by
// upstream in src/testvector.h (64/128-bit, seeds 0 and 1, 63-byte test key),
// plus class-API streaming/one-shot consistency.
#include <metrohash.h>       // 伞头（包含链完整性由本文件编译覆盖）
#include <metrohash64.h>
#include <metrohash128.h>

#include <cstdint>
#include <cstdio>

static int failures = 0;

static bool hex_eq(const uint8_t *hash, int nbytes, const char *hex) {
    static const char *digits = "0123456789ABCDEF";
    for (int i = 0; i < nbytes; ++i) {
        const char hi = digits[hash[i] >> 4];
        const char lo = digits[hash[i] & 0xF];
        if (hi != hex[2 * i] || lo != hex[2 * i + 1]) return false;
    }
    return true;
}

int main() {
    // 上游 src/testvector.h 官方 63 字节测试键
    static const char key63[] =
        "012345678901234567890123456789012345678901234567890123456789012";
    const uint64_t len = 63;
    uint8_t h64[8];
    uint8_t h128[16];

    // 1-4) 64-bit official vectors (seeds 0 and 1)
    metrohash64_1(reinterpret_cast<const uint8_t *>(key63), len, 0, h64);
    if (!hex_eq(h64, 8, "658F044F5C730E40")) { std::fprintf(stderr, "FAIL: metrohash64_1 seed0\n"); ++failures; }
    metrohash64_2(reinterpret_cast<const uint8_t *>(key63), len, 0, h64);
    if (!hex_eq(h64, 8, "073CAAB960623211")) { std::fprintf(stderr, "FAIL: metrohash64_2 seed0\n"); ++failures; }
    metrohash64_1(reinterpret_cast<const uint8_t *>(key63), len, 1, h64);
    if (!hex_eq(h64, 8, "AE49EBB0A856537B")) { std::fprintf(stderr, "FAIL: metrohash64_1 seed1\n"); ++failures; }
    metrohash64_2(reinterpret_cast<const uint8_t *>(key63), len, 1, h64);
    if (!hex_eq(h64, 8, "CF518E9CF58402C0")) { std::fprintf(stderr, "FAIL: metrohash64_2 seed1\n"); ++failures; }

    // 5-8) 128-bit official vectors (seeds 0 and 1)
    metrohash128_1(reinterpret_cast<const uint8_t *>(key63), len, 0, h128);
    if (!hex_eq(h128, 16, "ED9997ED9D0A8B0FF3F266399477788F")) { std::fprintf(stderr, "FAIL: metrohash128_1 seed0\n"); ++failures; }
    metrohash128_2(reinterpret_cast<const uint8_t *>(key63), len, 0, h128);
    if (!hex_eq(h128, 16, "7BBA6FE119CF35D45507EDF3505359AB")) { std::fprintf(stderr, "FAIL: metrohash128_2 seed0\n"); ++failures; }
    metrohash128_1(reinterpret_cast<const uint8_t *>(key63), len, 1, h128);
    if (!hex_eq(h128, 16, "DDA6BA67F7DE755EFDF6BEABECCFD1F4")) { std::fprintf(stderr, "FAIL: metrohash128_1 seed1\n"); ++failures; }
    metrohash128_2(reinterpret_cast<const uint8_t *>(key63), len, 1, h128);
    if (!hex_eq(h128, 16, "2DA6AF149A5CDBC12B09DB0846D69EF0")) { std::fprintf(stderr, "FAIL: metrohash128_2 seed1\n"); ++failures; }

    // 9) class API: streaming equals one-shot (MetroHash64)
    MetroHash64 hasher;
    hasher.Update(reinterpret_cast<const uint8_t *>(key63), len);
    uint8_t s64[8];
    hasher.Finalize(s64);
    uint8_t o64[8];
    MetroHash64::Hash(reinterpret_cast<const uint8_t *>(key63), len, o64);
    {
        bool same = true;
        for (int i = 0; i < 8; ++i) same = same && (s64[i] == o64[i]);
        if (!same) { std::fprintf(stderr, "FAIL: MetroHash64 streaming-vs-one-shot\n"); ++failures; }
    }

    // 10) class API: streaming equals one-shot (MetroHash128)
    MetroHash128 hasher128;
    hasher128.Update(reinterpret_cast<const uint8_t *>(key63), len);
    uint8_t s128[16];
    hasher128.Finalize(s128);
    uint8_t o128[16];
    MetroHash128::Hash(reinterpret_cast<const uint8_t *>(key63), len, o128);
    {
        bool same = true;
        for (int i = 0; i < 16; ++i) same = same && (s128[i] == o128[i]);
        if (!same) { std::fprintf(stderr, "FAIL: MetroHash128 streaming-vs-one-shot\n"); ++failures; }
    }

    if (failures == 0) {
        std::printf("PASS: metrohash 1.1.3 库链接和官方向量校验通过\n");
        return 0;
    }
    return 1;
}
