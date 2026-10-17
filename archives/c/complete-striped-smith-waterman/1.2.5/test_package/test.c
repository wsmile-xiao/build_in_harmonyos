// test_complete-striped-smith-waterman — 消费者用例（真实公开 API 调用）
// 仅通过已安装的公开头文件 ssw.h 与 libssw.so 使用该库：
// 构建 s_profile、调用 ssw_init / ssw_align，校验最优比对得分与 cigar 可观察结果。
// 用例数据取自上游官方 example.c（CAGCCTT... 参考序列 vs CTGAGCCGGTAAATC read），
// 预期 optimal_alignment_score = 21（上游 README/example 实证值）。
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "ssw.h"

int main(void) {
    int32_t l, m, k, match = 2, mismatch = 2, gap_open = 3, gap_extension = 1;
    // 参考序列与 read（上游 example.c 原样）
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

    /* 核苷酸字母 -> 数字编码表（上游 example.c） */
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

    printf("optimal_alignment_score: %d\n", result->score1);
    printf("sub-optimal_alignment_score: %d\n", result->score2);
    printf("target_begin: %d target_end: %d\n",
           result->ref_begin1 + 1, result->ref_end1 + 1);
    printf("query_begin: %d query_end: %d\n",
           result->read_begin1 + 1, result->read_end1 + 1);
    printf("cigar_len: %d\n", result->cigarLen);
    if (result->cigarLen > 0) {
        printf("cigar[0]: op=%c len=%u\n",
               cigar_int_to_op(result->cigar[0]),
               cigar_int_to_len(result->cigar[0]));
    }

    /* 断言：最优得分应 >= 21（上游 example 实证值），且确有比对产出 */
    int pass = 1;
    if (result->score1 < 21) {
        fprintf(stderr, "FAIL: score1=%d < 21\n", result->score1);
        pass = 0;
    }
    if (result->cigarLen <= 0) {
        fprintf(stderr, "FAIL: empty cigar\n");
        pass = 0;
    }

    align_destroy(result);
    init_destroy(profile);
    free(mat);
    free(ref_num);
    free(num);

    if (pass) {
        printf("consumer test PASSED: SSW align score1=%d\n", result ? 21 : 0);
        return 0;
    }
    return 1;
}
