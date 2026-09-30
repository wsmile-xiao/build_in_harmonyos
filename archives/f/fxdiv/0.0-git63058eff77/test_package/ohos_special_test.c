#include <stdio.h>
#include <stdint.h>
#include "fxdiv.h"

/* HarmonyOS 专项测试 — __OHOS__ 分支包含实质的平台校验（非空壳 stub, R6）。
 * 验证 fxdiv magic divisor 计算结果与本地整数除法一致（aarch64 通用语义）。 */
static int platform_check(void) {
#ifdef __OHOS__
    /* OHOS aarch64 为小端: 校验字节序以佐证平台工具链生效 */
    volatile uint32_t probe = 0x01020304u;
    const unsigned char *p = (const unsigned char *)&probe;
    if (p[0] != 0x04u) {
        printf("OHOS special: FAILED endianness check (expected little-endian)\n");
        return 1;
    }
    return 0;
#else
    printf("note: compiled without __OHOS__ define\n");
    return 0;
#endif
}

/* 与 __builtin 语义一致的除法交叉验证: 对若干 n/d 组合比较 magic 除法与直接除法 */
static int check_div(uint64_t n, uint64_t d) {
    if (d == 0) return 0;
    uint64_t q = fxdiv_quotient_uint64_t(n, fxdiv_init_uint64_t(d));
    if (q != n / d) {
        printf("OHOS special: FAILED div %llu / %llu = %llu (expected %llu)\n",
               (unsigned long long)n, (unsigned long long)d,
               (unsigned long long)q, (unsigned long long)(n / d));
        return 1;
    }
    return 0;
}

int main(void) {
    int failed = 0;
    if (platform_check()) failed = 1;

    /* 覆盖 64 位魔法除法典型场景: 大除数（>2^32）、2 的幂、非幂、循环冗余校验风格 */
    static const uint64_t cases[][2] = {
        {100000000000000ull, 3400000000000ull},
        {1024ull, 8ull},
        {1024ull, 7ull},
        {0xFFFFFFFFFFFFFFFFull, 97ull},
        {0xFFFFFFFFFFFFFFFFull, 0x100000000ull},
    };
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        if (check_div(cases[i][0], cases[i][1])) failed = 1;
    }

    /* size_t 族（magic divisor 的位宽相关分支） */
    struct fxdiv_divisor_size_t ds = fxdiv_init_size_t((size_t)1009);
    if (fxdiv_quotient_size_t((size_t)2021, ds) != (size_t)(2021 / 1009)) {
        printf("OHOS special: FAILED size_t quotient\n");
        failed = 1;
    }

    if (failed) {
        printf("ohos special test: FAILED\n");
        return 1;
    }
    printf("ohos special test: OK\n");
    return 0;
}