/*
 * libalgebra 1.1.0 HarmonyOS 专项测试（OHOS aarch64 工具链真实运行）。
 *
 * 独立于上游（上游无测试框架，仅 x86 专用 benchmark 样例）。本测试在
 * aarch64-unknown-linux-ohos clang 15 工具链下验证 libalgebra 公开 API
 * 的非 x86 代码路径（STORM_HAVE_CPUID 未定义时走 __builtin_popcountll
 * 与纯整数算法路径），断言可观察结果，确保头文件在 OHOS 交叉工具链下
 * 真实可用（patch 0001 守卫 <x86intrin.h> 后编译通过）。
 *
 * 注意 STORM_pospopcnt_u16 的 out[] 按下标=位位置（0..15）统计所有输入
 * 值中该位置 1 的总数，不能按数据值索引。
 */
#include <libalgebra.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    uint64_t a[4] = { 0xFFFFFFFFFFFFFFFFULL, 0xAAAAAAAAAAAAAAAAULL,
                      0x5555555555555555ULL, 0x0000000000000000ULL };
    uint64_t b[4] = { 0xFFFFFFFFFFFFFFFFULL, 0x5555555555555555ULL,
                      0xAAAAAAAAAAAAAAAAULL, 0x1111111111111111ULL };
    uint64_t expect_a_intersect_b = 0; /* 逐字与 */
    uint64_t expect_a_union_b = 0;
    uint64_t got_inter, got_union, got_diff;
    uint16_t u16data[8] = { 0x0000, 0xFFFF, 0x1234, 0xABCD,
                            0x0101, 0x8080, 0xFFFF, 0x0000 };
    uint32_t pos_cnt[16];
    uint32_t expect_pp[16];
    int i, bit, rc = 0;

    memset(expect_pp, 0, sizeof(expect_pp));
    for (i = 0; i < 8; ++i)
        for (bit = 0; bit < 16; ++bit)
            if (u16data[i] & (1u << bit))
                expect_pp[bit] += 1;

    for (i = 0; i < 4; ++i) {
        expect_a_intersect_b += STORM_popcount64(a[i] & b[i]);
        expect_a_union_b += STORM_popcount64(a[i] | b[i]);
    }

    got_inter = STORM_intersect_count(a, b, 4);
    got_union = STORM_union_count(a, b, 4);
    got_diff = STORM_diff_count(a, b, 4);

    printf("OHOS: intersect=%llu (expect %llu)\n",
           (unsigned long long)got_inter,
           (unsigned long long)expect_a_intersect_b);
    printf("OHOS: union=%llu (expect %llu)\n",
           (unsigned long long)got_union,
           (unsigned long long)expect_a_union_b);
    printf("OHOS: diff=%llu\n", (unsigned long long)got_diff);

    if (got_inter != expect_a_intersect_b) { fprintf(stderr, "FAIL: intersect\n"); rc = 1; }
    if (got_union != expect_a_union_b) { fprintf(stderr, "FAIL: union\n"); rc = 1; }

    STORM_pospopcnt_u16(u16data, 8, pos_cnt);
    for (bit = 0; bit < 16; ++bit) {
        if (pos_cnt[bit] != expect_pp[bit]) {
            fprintf(stderr, "FAIL: pospopcnt bit %d got %u expect %u\n",
                    bit, pos_cnt[bit], expect_pp[bit]);
            rc = 1;
        }
    }
    printf("OHOS: pospopcnt_u16 bit-position counts verified\n");

    if (rc == 0) printf("libalgebra OHOS 专项测试: OK\n");
    return rc;
}