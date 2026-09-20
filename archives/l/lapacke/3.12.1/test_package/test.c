/* lapacke 3.12.1 鸿蒙 PC 适配验证（独立 LAPACKE C 接口库，静态交付）。
 *
 * 直接 #include <lapacke.h>，链接本次交付的 liblapacke.a 与依赖包
 * lapack/3.12.1 的 liblapack/libblas/Fortran 运行时静态库，对每类能力做
 * 真实数值计算并校验结果——禁止只打印成功字符串的假测试。链接期即要求
 * liblapacke.a 真实提供全部被调 LAPACKE_* 接口、依赖包闭合全部 Fortran
 * 符号，防「头文件在但接口不在」。
 *
 * 8 项断言：
 *   1  LAPACKE_ilaver            版本锚定（v3.12.1 tag 版本字符串未更新，实测 3.12.0）
 *   2  LAPACKE_dgesv  colmajor   3x3 LU 分解解线性方程组
 *   3  LAPACKE_dgesv  rowmajor   行主序包装层（验证 LAPACKE 内部转置逻辑）
 *   4  LAPACKE_dpotrf+dpotrs     Cholesky 分解 + 三角求解回代
 *   5  LAPACKE_dgels  colmajor   最小二乘（3x2 超定方程组直线拟合）
 *   6  LAPACKE_dsyev  colmajor   对称特征值分解（含特征向量残差校验）
 *   7  LAPACKE_dgetrf 负例       奇异矩阵 → info=2（错误传播经 C 接口）
 *   8  LAPACKE_dpotrf 负例       非正定矩阵 → info=2
 */
#include <lapacke.h>

#include <math.h>
#include <stdio.h>

static int g_failed = 0;
static int g_total = 0;

static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

static int close_to(double a, double b) { return fabs(a - b) < 1e-9; }

int main(void) {
    /* ── 1. LAPACKE_ilaver：版本锚定（上游发布怪癖）──────────────────────── */
    {
        /* v3.12.1 官方 tarball（sha256 2ca6407a…）的 INSTALL/ilaver.f 与
         * CMakeLists.txt 均停留在 3.12.0（上游 tag 未随发布更新版本字符串），
         * ILAVER 实测返回 (3,12,0)。此处按源码树真实行为锚定，兼防上游
         * 更换 tarball 造成版本漂移而测试仍然通过。 */
        lapack_int vm = 0, vn = 0, vp = 0;
        LAPACKE_ilaver(&vm, &vn, &vp);
        int ok = (vm == 3 && vn == 12 && vp == 0);
        char buf[128];
        snprintf(buf, sizeof(buf), "LAPACK 版本 %ld.%ld.%ld（v3.12.1 tag 字符串未更新，期望 3.12.0）",
                 (long)vm, (long)vn, (long)vp);
        check(ok, "LAPACKE_ilaver 版本锚定", buf);
    }

    /* ── 2. LAPACKE_dgesv colmajor：A=[[2,1,0],[1,3,1],[0,1,2]]，b=[3,5,3] ── */
    {
        lapack_int n = 3, nrhs = 1, lda = 3, ldb = 3;
        lapack_int ipiv[3];
        double A[9] = {2.0, 1.0, 0.0,   1.0, 3.0, 1.0,   0.0, 1.0, 2.0}; /* 列主序 */
        double b[3] = {3.0, 5.0, 3.0};
        lapack_int info = LAPACKE_dgesv(LAPACK_COL_MAJOR, n, nrhs, A, lda, ipiv, b, ldb);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld x=[%.4f %.4f %.4f] 期望 [1 1 1]",
                 (long)info, b[0], b[1], b[2]);
        check(info == 0 && close_to(b[0], 1.0) && close_to(b[1], 1.0) && close_to(b[2], 1.0),
              "LAPACKE_dgesv colmajor 解线性方程组", buf);
    }

    /* ── 3. LAPACKE_dgesv rowmajor：同一方程组的行主序形态 ────────────────── */
    {
        /* nrhs=1 时取 ldb=nrhs=1：b 的 3 个元素连续存放（行主序存储声明，
         * ldb>=nrhs 即可；与上游 example 的存储约定一致）。 */
        lapack_int n = 3, nrhs = 1, lda = 3, ldb = 1;
        lapack_int ipiv[3];
        double A[9] = {2.0, 1.0, 0.0,   1.0, 3.0, 1.0,   0.0, 1.0, 2.0}; /* 行主序同布局 */
        double b[3] = {3.0, 5.0, 3.0};
        lapack_int info = LAPACKE_dgesv(LAPACK_ROW_MAJOR, n, nrhs, A, lda, ipiv, b, ldb);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld x=[%.4f %.4f %.4f] 期望 [1 1 1]",
                 (long)info, b[0], b[1], b[2]);
        check(info == 0 && close_to(b[0], 1.0) && close_to(b[1], 1.0) && close_to(b[2], 1.0),
              "LAPACKE_dgesv rowmajor 行主序包装", buf);
    }

    /* ── 4. LAPACKE_dpotrf + LAPACKE_dpotrs：A=[[4,2],[2,3]]，b=[1,2] ─────── */
    {
        lapack_int n = 2, nrhs = 1, lda = 2, ldb = 2;
        double A[4] = {4.0, 2.0, 2.0, 3.0}; /* 列主序，正定 */
        double b[2] = {1.0, 2.0};
        lapack_int info = LAPACKE_dpotrf(LAPACK_COL_MAJOR, 'L', n, A, lda);
        int ok = (info == 0) && close_to(A[0], 2.0) && close_to(A[1], 1.0)
                 && close_to(A[3], sqrt(2.0));
        /* LL^T x = b → x = [-0.125, 0.75] */
        info = LAPACKE_dpotrs(LAPACK_COL_MAJOR, 'L', n, nrhs, A, lda, b, ldb);
        ok = ok && info == 0 && close_to(b[0], -0.125) && close_to(b[1], 0.75);
        char buf[128];
        snprintf(buf, sizeof(buf), "info=%ld L[0]=2 L[1,0]=1 L[1,1]=√2；x=[%.4f %.4f] 期望 [-0.125 0.75]",
                 (long)info, b[0], b[1]);
        check(ok, "LAPACKE_dpotrf+dpotrs Cholesky 分解与三角求解", buf);
    }

    /* ── 5. LAPACKE_dgels colmajor：(0,1),(1,1),(2,3) 拟合 y=a+bt ─────────── */
    {
        /* 最小二乘正解：a=2/3, b=1 */
        lapack_int m = 3, n = 2, nrhs = 1, lda = 3, ldb = 3;
        double A[6] = {1.0, 1.0, 1.0,   0.0, 1.0, 2.0}; /* 列主序 3x2 */
        double b[3] = {1.0, 1.0, 3.0};
        lapack_int info = LAPACKE_dgels(LAPACK_COL_MAJOR, 'N', m, n, nrhs, A, lda, b, ldb);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld x=[a=%.4f b=%.4f] 期望 [0.6667 1.0000]",
                 (long)info, b[0], b[1]);
        check(info == 0 && close_to(b[0], 2.0 / 3.0) && close_to(b[1], 1.0),
              "LAPACKE_dgels 最小二乘（超定 3x2）", buf);
    }

    /* ── 6. LAPACKE_dsyev colmajor：A=[[2,1],[1,2]] 特征值 {1,3} ──────────── */
    {
        lapack_int n = 2, lda = 2;
        double A[4] = {2.0, 1.0, 1.0, 2.0}; /* 列主序 */
        double w[2] = {0.0, 0.0};
        lapack_int info = LAPACKE_dsyev(LAPACK_COL_MAJOR, 'V', 'U', n, A, lda, w);
        int ok = info == 0 && close_to(w[0], 1.0) && close_to(w[1], 3.0);
        /* 特征向量残差：A·v_k − λ_k·v_k ≈ 0（列主序，v_k = A 的第 k 列） */
        if (ok) {
            for (lapack_int k = 0; k < n && ok; k++) {
                double v0 = A[2 * k], v1 = A[2 * k + 1];
                double r0 = 2.0 * v0 + 1.0 * v1 - w[k] * v0;
                double r1 = 1.0 * v0 + 2.0 * v1 - w[k] * v1;
                ok = fabs(r0) < 1e-8 && fabs(r1) < 1e-8;
            }
        }
        char buf[128];
        snprintf(buf, sizeof(buf), "info=%ld 特征值={%.4f, %.4f} 残差<1e-8",
                 (long)info, w[0], w[1]);
        check(ok, "LAPACKE_dsyev 对称特征值分解+特征向量残差", buf);
    }

    /* ── 7. LAPACKE_dgetrf 负例：奇异矩阵 → info=2 ────────────────────────── */
    {
        lapack_int m = 2, n = 2, lda = 2;
        lapack_int ipiv[2];
        double A[4] = {1.0, 2.0, 2.0, 4.0}; /* A=[[1,2],[2,4]] 奇异 */
        lapack_int info = LAPACKE_dgetrf(LAPACK_COL_MAJOR, m, n, A, lda, ipiv);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld 期望 2", (long)info);
        check(info == 2, "LAPACKE_dgetrf 负例（奇异 → info>0）", buf);
    }

    /* ── 8. LAPACKE_dpotrf 负例：非正定矩阵 → info=2 ──────────────────────── */
    {
        lapack_int n = 2, lda = 2;
        double A[4] = {1.0, 2.0, 2.0, 1.0}; /* A=[[1,2],[2,1]] 非正定 */
        lapack_int info = LAPACKE_dpotrf(LAPACK_COL_MAJOR, 'L', n, A, lda);
        char buf[96];
        snprintf(buf, sizeof(buf), "info=%ld 期望 2", (long)info);
        check(info == 2, "LAPACKE_dpotrf 负例（非正定 → info>0）", buf);
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
