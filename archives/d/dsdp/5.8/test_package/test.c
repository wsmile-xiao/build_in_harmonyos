/* DSDP 5.8 鸿蒙 PC 适配验证。
 *
 * R34：不做空壳探测——直接 #include <dsdp5.h>、直接链接 libdsdp，
 * 并**真解一个半定规划问题**，校验最优值与已知解析解一致。
 *
 * 问题（标准 SDP 对偶形式，DSDP 的原生形式）：
 *     max  b'y   s.t.  C - sum_i y_i A_i  >= 0 (半正定)
 * 取 1 个变量、2x2 的块：
 *     C = diag(1, 3),  A_1 = I,  b = 1
 *   约束即 diag(1-y, 3-y) >= 0  →  y <= 1，目标 max y  →  y* = 1
 * 这条路径会走到 DSDP 的内点迭代与稠密矩阵运算（后者用 BLAS/LAPACK）。
 */
#include <dsdp5.h>

#include <math.h>
#include <stdio.h>

static int g_failed = 0, g_total = 0;
static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

int main(void) {
    char buf[192];
    DSDP dsdp = NULL;
    SDPCone sdpcone = NULL;
    int info;

    /* 1 个 y 变量 */
    info = DSDPCreate(1, &dsdp);
    check(info == 0, "DSDPCreate", NULL);
    if (info) return 1;

    info = DSDPCreateSDPCone(dsdp, 1, &sdpcone);      /* 1 个块 */
    check(info == 0, "DSDPCreateSDPCone", NULL);

    info = SDPConeSetBlockSize(sdpcone, 0, 2);        /* 块大小 2x2 */
    check(info == 0, "SDPConeSetBlockSize(2)", NULL);

    /* DSDP 用打包的下三角存对称阵：2x2 → 3 个元素 [a00, a10, a11] */
    static double Cmat[3] = {1.0, 0.0, 3.0};          /* C = diag(1,3) */
    static double A1mat[3] = {1.0, 0.0, 1.0};         /* A_1 = I       */

    info  = SDPConeSetADenseVecMat(sdpcone, 0, 0, 2, 1.0, Cmat, 3);   /* 索引 0 = C */
    info += SDPConeSetADenseVecMat(sdpcone, 0, 1, 2, 1.0, A1mat, 3);  /* 索引 1 = A_1 */
    check(info == 0, "SDPConeSetADenseVecMat(C, A1)", NULL);

    info = DSDPSetDualObjective(dsdp, 1, 1.0);        /* b_1 = 1 */
    check(info == 0, "DSDPSetDualObjective", NULL);

    info = DSDPSetup(dsdp);
    check(info == 0, "DSDPSetup", NULL);

    info = DSDPSolve(dsdp);
    check(info == 0, "DSDPSolve 求解完成", NULL);

    DSDPTerminationReason reason;
    DSDPStopReason(dsdp, &reason);

    double y = 0.0;
    DSDPGetY(dsdp, &y, 1);
    double pobj = 0, dobj = 0;
    DSDPGetPObjective(dsdp, &pobj);
    DSDPGetDObjective(dsdp, &dobj);

    snprintf(buf, sizeof(buf), "y=%.6f 期望 1.0（终止原因 %d，pobj=%.6f dobj=%.6f）",
             y, (int)reason, pobj, dobj);
    check(fabs(y - 1.0) < 1e-4, "解得 y* = 1（已知解析解）", buf);

    DSDPDestroy(dsdp);

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
