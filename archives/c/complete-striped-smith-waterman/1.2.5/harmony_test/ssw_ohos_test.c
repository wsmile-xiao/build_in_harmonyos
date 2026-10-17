// ssw_ohos_test.c — HarmonyOS 专项测试（OHOS aarch64 / sse2neon NEON 路径）
// 独立于上游示例程序与 test_package 消费者用例的专项验证：
// 只使用官方公开头文件 ssw.h 与公开 API（ssw_init / ssw_align / init_destroy /
// align_destroy / cigar_int_to_op / cigar_int_to_len），验证在 OHOS aarch64
// （SSE2 指令由 sse2neon.h 翻译到 NEON）上编译、链接、运行并产生可观察结果。
// 断言基于上游官方实证值：example.c 中 CAGCCTT... 参考序列 vs CTGAGCCGGTAAATC
// read 的 optimal_alignment_score = 21（上游 README/example 固定输出）。
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "ssw.h"

/* 核苷酸字母 -> 数字编码表（上游 example.c 原样） */
static const int8_t nt_table[128] = {
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 0, 4, 1,  4, 4, 4, 2,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  3, 0, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 0, 4, 1,  4, 4, 4, 2,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  3, 0, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4
};

int main(void) {
    int32_t l, m, k, match = 2, mismatch = 2, gap_open = 3, gap_extension = 1;
    static const char ref_seq[40] = {'C', 'A', 'G', 'C', 'C', 'T', 'T', 'T', 'C', 'T',
                                     'G', 'A', 'C', 'C', 'C', 'G', 'G', 'A', 'A', 'A',
                                     'T', 'C', 'A', 'A', 'A', 'A', 'T', 'A', 'G', 'G',
                                     'C', 'A', 'C', 'A', 'A', 'C', 'A', 'A', 'A', '\0'};
    static const char read_seq[16] = {'C', 'T', 'G', 'A', 'G', 'C', 'C', 'G',
                                      'G', 'T', 'A', 'A', 'A', 'T', 'C', '\0'};
    s_profile* profile;
    int8_t* num = (int8_t*)malloc(16);
    int8_t* ref_num = (int8_t*)malloc(64);
    s_align* result;

    /* 基因组打分矩阵：A/C/G/T 匹配 +2，错配 -2，简并碱基 0 */
    int8_t* mat = (int8_t*)calloc(25, sizeof(int8_t));
    for (l = k = 0; l < 4; ++l) {
        for (m = 0; m < 4; ++m) mat[k++] = l == m ? match : -mismatch;
        mat[k++] = 0;
    }
    for (m = 0; m < 5; ++m) mat[k++] = 0;

    for (m = 0; m < 15; ++m) num[m] = nt_table[(int)read_seq[m]];
    profile = ssw_init(num, 15, mat, 5, 2);
    if (!profile) {
        fprintf(stderr, "FAIL: ssw_init returned NULL\n");
        return 1;
    }
    for (m = 0; m < 39; ++m) ref_num[m] = nt_table[(int)ref_seq[m]];

    result = ssw_align(profile, ref_num, 39, gap_open, gap_extension, 1, 0, 0, 15);
    if (!result) {
        fprintf(stderr, "FAIL: ssw_align returned NULL\n");
        init_destroy(profile);
        return 1;
    }

    printf("OHOS test: score1=%d score2=%d target_end=%d query_end=%d cigar_len=%d\n",
           result->score1, result->score2, result->ref_end1, result->read_end1,
           result->cigarLen);

    /* 断言 1: 最优得分 >= 上游实证值 21 */
    if (result->score1 < 21) {
        fprintf(stderr, "FAIL: score1=%d < 21\n", result->score1);
        return 1;
    }
    /* 断言 2: cigar 非空且首个 op 为合法编码（M/I/D 之一） */
    if (result->cigarLen <= 0) {
        fprintf(stderr, "FAIL: empty cigar\n");
        return 1;
    }
    char op = cigar_int_to_op(result->cigar[0]);
    uint32_t op_len = cigar_int_to_len(result->cigar[0]);
    if (op != 'M' && op != 'I' && op != 'D') {
        fprintf(stderr, "FAIL: invalid cigar op %c\n", op);
        return 1;
    }
    if (op_len == 0) {
        fprintf(stderr, "FAIL: zero-length first cigar op\n");
        return 1;
    }
    /* 断言 3: 比对端点单调有效（target_end/query_end 落在序列长度内） */
    if (result->ref_end1 < 0 || result->ref_end1 >= 39 ||
        result->read_end1 < 0 || result->read_end1 >= 15) {
        fprintf(stderr, "FAIL: out-of-range alignment end (ref_end1=%d read_end1=%d)\n",
                result->ref_end1, result->read_end1);
        return 1;
    }

    printf("HarmonyOS special test PASSED: optimal score %d (>=21), cigar op=%c len=%u\n",
           result->score1, op, op_len);

    align_destroy(result);
    init_destroy(profile);
    free(mat);
    free(ref_num);
    free(num);
    return 0;
}
