/* lapacke64 3.12.1 鸿蒙 PC 适配验证（Reference-LAPACK ILP64 变体）。
 *
 * 直接 #include <lapacke.h>、直接链接本次交付的 liblapacke64/liblapack64/
 * libblas64（+ 随包 flang Fortran 运行时归档），并对每类能力做真实数值计算
 * 且校验结果——禁止只打印成功字符串的假测试。链接期即要求库真实导出全部
 * 被调 LAPACKE_* 符号，防「头文件在但接口不在」。
 *
 * 编译口径：-DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H（recipe cpp_info.defines
 * 传播）——lapack_int=int64_t。若宏口径丢失，断言 1 直接失败。
 *
 * 8 项断言：
 *   1  sizeof(lapack_int)==8       ILP64 ABI 锁定（静态+运行期双重）
 *   2  LAPACKE_ilaver              版本一致性（v3.12.1 tag 内置 3.12.0）
 *   3  LAPACKE_dgesv  colmajor     LU 分解解线性方程组
 *   4  LAPACKE_dgesv  rowmajor     行主序包装层（验证 LAPACKE 内部转置逻辑）
 *   5  LAPACKE_dpotrf colmajor     Cholesky 分解
 *   6  LAPACKE_dgels  colmajor     最小二乘（4x2 超定方程组，QR 路径）
 *   7  LAPACKE_dgeev  colmajor     非对称特征值+特征向量（重量级 Fortran 路径，残差校验）
 *   8  LAPACKE_dpotrf 负例          非正定矩阵返回 info=2（错误传播经 C 接口）
 */
#include <lapacke.h>

#include <math.h>
#include <stdio.h>

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(lapack_int) == 8, "lapacke64 requires lapack_int to be int64_t");
#endif

static int g_failed = 0;
static int g_total = 0;

static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

static int close_to(double a, double b) { return fabs(a - b) < 1e-6; }

int main(void) {
    /* ── 1. ILP64 ABI 锁定：lapack_int 必须是 8 字节 ──────────────────────── */
    {
        char buf[96];
        snprintf(buf, sizeof(buf), "sizeof(lapack_int)=%zu sizeof(lapack_logical)=%zu 期望 8/8",
                 sizeof(lapack_int), sizeof(lapack_logical));
        check(sizeof(lapack_int) == 8 && sizeof(lapack_logical) == 8,
              "ILP64 ABI 锁定", buf);
    }

    /* ── 2. LAPACKE_ilaver：tarball 内置版本（3.12.1 tag 未提升，仍 3.12.0）─ */
    {
        lapack_int vm = 0, vn = 0, vp = 0;
        LAPACKE_ilaver(&vm, &vn, &vp);
        int ok = (vm == 3 && vn == 12 && vp == 0);
        char buf[96];
        snprintf(buf, sizeof(buf), "LAPACK 版本 %ld.%ld.%ld 期望 3.12.0（tag 内置值）",
                 (long)vm, (long)vn, (long)vp);
        check(ok, "LAPACKE_ilaver 版本一致性", buf);
    }

    /* ── 3. LAPACKE_dgesv colmajor：Ax=b，A=[2 1;1 3]，b=[3;5] → x=[0.8;1.4] ── */
    {
        lapack_int n = 2, nrhs = 1, lda = 2, ldb = 2;
        lapack_int ipiv[2];
        double A[4] = {2.0, 1.0, 1.0, 3.0}; /* 列主序 */
        double b[2] = {3.0, 5.0};
        lapack_int info = LAPACKE_dgesv(LAPACK_COL_MAJOR, n, nrhs, A, lda, ipiv, b, ldb);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld x=[%.4f %.4f] 期望 [0.8000 1.4000]",
                 (long)info, b[0], b[1]);
        check(info == 0 && close_to(b[0], 0.8) && close_to(b[1], 1.4),
              "LAPACKE_dgesv colmajor 解线性方程组", buf);
    }

    /* ── 4. LAPACKE_dgesv rowmajor：同一方程组的行主序形态 ────────────────── */
    {
        /* 行主序存储规则：b 为 2x1 矩阵，第 i 行位于 b[i*ldb]。nrhs=1 时取
         * ldb=1（LAPACKE 仅要求 ldb>=nrhs），b 恰好连续存放；若取 ldb=2 则
         * 行 1 位于 b[2]，超出 2 元素缓冲（上游 dge_trans 越界读）——是调用
         * 方存储声明错误，非库缺陷。 */
        lapack_int n = 2, nrhs = 1, lda = 2, ldb = 1;
        lapack_int ipiv[2];
        double A[4] = {2.0, 1.0, 1.0, 3.0}; /* 行主序（数值碰巧相同） */
        double b[2] = {3.0, 5.0};
        lapack_int info = LAPACKE_dgesv(LAPACK_ROW_MAJOR, n, nrhs, A, lda, ipiv, b, ldb);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld x=[%.4f %.4f] 期望 [0.8000 1.4000]",
                 (long)info, b[0], b[1]);
        check(info == 0 && close_to(b[0], 0.8) && close_to(b[1], 1.4),
              "LAPACKE_dgesv rowmajor 行主序包装", buf);
    }

    /* ── 5. LAPACKE_dpotrf colmajor：A=[4 2;2 5]（正定）→ L=[2 0;1 2] ─────── */
    {
        lapack_int n = 2, lda = 2;
        double A[4] = {4.0, 2.0, 2.0, 5.0};
        lapack_int info = LAPACKE_dpotrf(LAPACK_COL_MAJOR, 'L', n, A, lda);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld L=[%.1f 0; %.1f %.1f] 期望 [2 0; 1 2]",
                 (long)info, A[0], A[1], A[3]);
        check(info == 0 && close_to(A[0], 2.0) && close_to(A[1], 1.0) && close_to(A[3], 2.0),
              "LAPACKE_dpotrf Cholesky 分解", buf);
    }

    /* ── 6. LAPACKE_dgels colmajor：最小二乘直线拟合 ──────────────────────── */
    {
        /* (t,y) = (0,0),(1,1),(2,1),(3,2) 拟合 y = a + b·t → a=0.1, b=0.6 */
        lapack_int m = 4, n = 2, nrhs = 1, lda = 4, ldb = 4;
        double A[8] = {1.0, 1.0, 1.0, 1.0,   0.0, 1.0, 2.0, 3.0}; /* 列主序 4x2 */
        double b[4] = {0.0, 1.0, 1.0, 2.0};
        lapack_int info = LAPACKE_dgels(LAPACK_COL_MAJOR, 'N', m, n, nrhs, A, lda, b, ldb);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld x=[%.4f %.4f] 期望 [0.1000 0.6000]",
                 (long)info, b[0], b[1]);
        check(info == 0 && close_to(b[0], 0.1) && close_to(b[1], 0.6),
              "LAPACKE_dgels 最小二乘（超定 4x2）", buf);
    }

    /* ── 7. LAPACKE_dgeev colmajor：A=[2 1;0 3] 的特征值 {2,3} + 残差校验 ─── */
    {
        lapack_int n = 2, lda = 2, ldvl = 2, ldvr = 2;
        double A[4] = {2.0, 0.0, 1.0, 3.0}; /* 列主序 → 矩阵 [[2,1],[0,3]] */
        double wr[2] = {0, 0}, wi[2] = {0, 0};
        double vl[4] = {0, 0, 0, 0}, vr[4] = {0, 0, 0, 0};
        lapack_int info = LAPACKE_dgeev(LAPACK_COL_MAJOR, 'N', 'V', n, A, lda,
                                        wr, wi, vl, ldvl, vr, ldvr);
        int ok = (info == 0) && fabs(wi[0]) < 1e-9 && fabs(wi[1]) < 1e-9 &&
                 close_to(wr[0], 2.0) && close_to(wr[1], 3.0);
        /* 特征向量残差：A·v_k − λ_k·v_k ≈ 0（k=0,1；A 对称作用手写展开） */
        if (ok) {
            for (int k = 0; k < 2 && ok; k++) {
                double v0 = vr[2 * k], v1 = vr[2 * k + 1];
                double r0 = 2.0 * v0 + 1.0 * v1 - wr[k] * v0;
                double r1 = 0.0 * v0 + 3.0 * v1 - wr[k] * v1;
                ok = fabs(r0) < 1e-8 && fabs(r1) < 1e-8;
            }
        }
        char buf[128];
        snprintf(buf, sizeof(buf), "info=%ld 特征值={%.4f, %.4f} 虚部≈0 残差<1e-8",
                 (long)info, wr[0], wr[1]);
        check(ok, "LAPACKE_dgeev 非对称特征值+特征向量残差", buf);
    }

    /* ── 8. LAPACKE_dpotrf 负例：非正定矩阵 → info=2（错误传播经 C 接口）──── */
    {
        lapack_int n = 2, lda = 2;
        double A[4] = {1.0, 2.0, 2.0, 1.0}; /* A=[1 2;2 1] 非正定 */
        lapack_int info = LAPACKE_dpotrf(LAPACK_COL_MAJOR, 'L', n, A, lda);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld 期望 2", (long)info);
        check(info == 2, "LAPACKE_dpotrf 负例（非正定 → info>0）", buf);
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
