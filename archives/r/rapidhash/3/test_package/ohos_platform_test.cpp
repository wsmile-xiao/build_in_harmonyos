/* ohos_platform_test.cpp — rapidhash/3 鸿蒙平台专项验证（aarch64 OHOS）。
 *
 * 1. 平台宏报告与断言（OHOS 工具链预定义 __unix__/__linux__）
 * 2. 小端序：运行时探测与头文件内部 RAPIDHASH_LITTLE_ENDIAN 判定一致
 * 3. __SIZEOF_INT128__ 存在（rapid_mum 走 128 位乘法路径）且行为正确
 * 4. 非对齐偏移哈希 == 对齐哈希（memcpy 装载语义）
 * 5. KAT 抽查（空输入 / 固定向量 / seeded）
 */
#include <rapidhash/rapidhash.h>

#include <cstdio>
#include <cstring>

int main(void) {
    int fails = 0, pass = 0;

    /* 1) platform macros */
#if !defined(__unix__) && !defined(__linux__) && !defined(__OHOS__)
    std::printf("FAIL: no POSIX platform macro (__unix__/__linux__/__OHOS__)\n");
    fails++;
#else
    pass++;
#endif
#if defined(__aarch64__) || defined(__ARM_64BIT_STATE)
    pass++;
#else
    std::printf("FAIL: expected aarch64 target\n");
    fails++;
#endif
    std::printf("platform: OHOS/aarch64 (__unix__=%d __linux__=%d __OHOS__=%d)\n",
#if defined(__unix__)
                1,
#else
                0,
#endif
#if defined(__linux__)
                1,
#else
                0,
#endif
#if defined(__OHOS__)
                1
#else
                0
#endif
    );

    /* 2) endianness agreement with the header's own detection */
    {
        const uint32_t probe = 1u;
        const int runtime_le = (*reinterpret_cast<const uint8_t *>(&probe) == 1u);
#ifdef RAPIDHASH_LITTLE_ENDIAN
        if (runtime_le) { pass++; }
        else { std::printf("FAIL: header LE but runtime BE\n"); fails++; }
#else
        if (!runtime_le) { pass++; }
        else { std::printf("FAIL: header BE but runtime LE\n"); fails++; }
#endif
    }

    /* 3) 128-bit integer path (used by rapid_mum on clang/aarch64) */
#if defined(__SIZEOF_INT128__)
    {
        if (sizeof(unsigned __int128) == 16) { pass++; }
        else { std::printf("FAIL: __int128 size=%zu\n", sizeof(unsigned __int128)); fails++; }
        const unsigned __int128 m =
            (static_cast<unsigned __int128>(0xFFFFFFFFULL) * 0xFFFFFFFFULL);
        if (static_cast<uint64_t>(m) == 0xFFFFFFFE00000001ULL) { pass++; }
        else { std::printf("FAIL: 128-bit multiply value\n"); fails++; }
    }
#else
    std::printf("FAIL: __SIZEOF_INT128__ missing (rapid_mum fallback path)\n");
    fails++;
#endif

    /* 4) unaligned-offset hashing equals aligned hashing for identical bytes:
     *    the same byte sequence copied to an odd offset must hash the same
     *    (loads go through memcpy, so alignment must not change results) */
    {
        static uint8_t base[512];
        static uint8_t shifted[513]; /* shifted[i+1] == base[i] */
        for (size_t i = 0; i < sizeof(base); i++) {
            base[i] = (uint8_t)((i * 13 + 5) & 0xFF);
            shifted[i + 1] = base[i];
        }
        static const size_t ls[] = {1, 7, 8, 63, 200};
        for (size_t i = 0; i < sizeof(ls) / sizeof(ls[0]); i++) {
            const size_t n = ls[i];
            const uint64_t from_aligned = rapidhash(base, n);
            const uint64_t from_unaligned = rapidhash(shifted + 1, n);
            if (from_aligned == from_unaligned) { pass++; }
            else {
                std::printf("FAIL: unaligned hash mismatch at len=%zu\n", n); fails++;
            }
        }
    }

    /* 5) KAT spot checks */
    if (rapidhash("", 0) == 0x0338dc4be2cecdaeULL) { pass++; }
    else { std::printf("FAIL: KAT empty input\n"); fails++; }
    if (rapidhash("hello world", 11) == rapidhashMicro("hello world", 11)) { pass++; }
    else { std::printf("FAIL: KAT hello-world Micro equivalence\n"); fails++; }
    if (rapidhash_withSeed("hello world", 11, 0x9E3779B97F4A7C15ULL) !=
        rapidhash_withSeed("hello world", 11, 0)) {
        pass++;
    } else {
        std::printf("FAIL: seeded hash equals unseeded\n"); fails++;
    }

    std::printf("%s: %d checks passed, %d failed (HarmonyOS platform tests)\n",
                fails ? "FAIL" : "OK", pass, fails);
    return fails ? 1 : 0;
}
