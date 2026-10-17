/* CMR 真实断言：跑它的主业——判一个矩阵是不是全幺模（totally unimodular）。
 *
 * 两个 2x2 矩阵，答案手算即得：
 *   A = [[1, 1], [1, -1]]  det = -2  → 不是全幺模
 *   B = [[1, 1], [0,  1]]  所有子式 ∈ {0,±1} → 是全幺模
 * 两个都要判对才算通过 —— 只判一个的话，一个恒返回 true（或 false）的空壳也能蒙混。
 */
#include <stdio.h>
#include <stdbool.h>
#include <cmr/env.h>
#include <cmr/matrix.h>
#include <cmr/tu.h>

#define CHECK(call) do { \
    CMR_ERROR _e = (call); \
    if (_e != CMR_OKAY) { fprintf(stderr, "cmr: %s 失败，错误码 %d\n", #call, (int)_e); return 1; } \
} while (0)

/* 建一个 2x2 稠密矩阵（4 个非零）。values 按行优先给。 */
static CMR_ERROR make2x2(CMR* cmr, CMR_CHRMAT** out, signed char v00, signed char v01,
                         signed char v10, signed char v11)
{
    size_t nnz = 0;
    signed char vals[4] = {v00, v01, v10, v11};
    for (int i = 0; i < 4; ++i) if (vals[i]) ++nnz;

    CMR_ERROR e = CMRchrmatCreate(cmr, out, 2, 2, (int)nnz);
    if (e != CMR_OKAY) return e;
    CMR_CHRMAT* m = *out;
    size_t k = 0;
    for (size_t row = 0; row < 2; ++row) {
        m->rowSlice[row] = k;
        for (size_t col = 0; col < 2; ++col) {
            signed char v = vals[row * 2 + col];
            if (!v) continue;
            m->entryColumns[k] = col;
            m->entryValues[k] = v;
            ++k;
        }
    }
    m->rowSlice[2] = k;
    return CMR_OKAY;
}

static int check(CMR* cmr, const char* label, signed char a, signed char b,
                 signed char c, signed char d, bool expected)
{
    CMR_CHRMAT* m = NULL;
    if (make2x2(cmr, &m, a, b, c, d) != CMR_OKAY) {
        fprintf(stderr, "cmr: 建 %s 矩阵失败\n", label);
        return 1;
    }
    bool isTU = !expected;   /* 先置成相反值，确保结论真是算出来的 */
    CMR_ERROR e = CMRtuTest(cmr, m, &isTU, NULL, NULL, NULL, NULL, 60.0);
    CMRchrmatFree(cmr, &m);
    if (e != CMR_OKAY) {
        fprintf(stderr, "cmr: CMRtuTest(%s) 出错，错误码 %d\n", label, (int)e);
        return 1;
    }
    printf("cmr: %s 全幺模 = %s（期望 %s）\n", label, isTU ? "是" : "否", expected ? "是" : "否");
    if (isTU != expected) {
        fprintf(stderr, "cmr: %s 判错了\n", label);
        return 1;
    }
    return 0;
}

int main(void)
{
    CMR* cmr = NULL;
    CHECK(CMRcreateEnvironment(&cmr));

    int bad = 0;
    bad |= check(cmr, "A=[[1,1],[1,-1]] (det=-2)", 1, 1, 1, -1, false);
    bad |= check(cmr, "B=[[1,1],[0,1]]",            1, 1, 0,  1, true);

    CHECK(CMRfreeEnvironment(&cmr));
    if (bad) return 1;
    printf("cmr: 全部断言通过\n");
    return 0;
}
