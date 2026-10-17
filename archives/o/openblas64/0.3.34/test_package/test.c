/* OpenBLAS64 0.3.34 鸿蒙 PC 适配验证（ILP64：64 位整型接口）。
 *
 * R34：不做「dlopen + dlsym 看指针非空」的空壳探测——那只证明符号存在，不证明能算对。
 * 本文件直接 #include OpenBLAS64 公共头（cblas.h/lapacke.h/lapack.h）、直接链接
 * libopenblas64，并对每类能力做**真实数值计算且校验结果**：
 *   · BLAS    cblas_ddot / cblas_dgemm        —— C 接口（ILP64 下整型参数为 64 位）
 *   · LAPACK  LAPACK_dgesv / LAPACK_dpotrf    —— Fortran 接口（lapack.h 声明，ILP64
 *                                                下 lapack_int 为 64 位）
 *   · LAPACKE LAPACKE_dgesv                   —— C 接口
 *   · ILP64   sizeof(lapack_int)==8 + 配置串含 0.3.34
 *
 * ILP64 注意：本包以 INTERFACE64=1 构建，blasint/lapack_int 均为 64 位。
 * 测试中整型一律用 lapack_int / int64_t，不用 plain int，避免 AArch64 上
 * 32 位与 64 位 ABI 混用导致高 32 位未定义。
 *
 * ILP64 消费者契约：lapack_int 宽度由 LAPACK_ILP64 决定（上游 lapacke.h/lapack.h
 * 侧宏），必须在 include 之前定义；blasint 宽度由包内 openblas_config.h 的
 * OPENBLAS_USE64BITINT 决定（库侧宏，INTERFACE64=1 产生），此处不手动定义、
 * 只做存在性校验，避免掩盖库侧未开 ILP64 的问题。
 */
#ifndef LAPACK_ILP64
#define LAPACK_ILP64
#endif
#include <openblas_config.h>
#ifndef OPENBLAS_USE64BITINT
#error "openblas64 包的 openblas_config.h 缺少 OPENBLAS_USE64BITINT：库侧未以 INTERFACE64=1 构建"
#endif
#include <cblas.h>
#include <lapacke.h>
#include <lapack.h>

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern char *openblas_get_config(void);
extern int openblas_get_num_threads(void);
extern void openblas_set_num_threads(int num_threads);

static int g_failed = 0;
static int g_total = 0;

static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " -- " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

static int close_to(double a, double b) { return fabs(a - b) < 1e-6; }

int main(void) {
    char buf[320];
    /* 单线程跑数值校验：避免真机多线程/亲和性抖动掩盖计算正确性；库仍为多线程构建。 */
    openblas_set_num_threads(1);
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *cfg = openblas_get_config();
    printf("OpenBLAS64 config: %s\n", cfg ? cfg : "(null)");
    printf("threads: %d\n", openblas_get_num_threads());
    printf("sizeof(blasint)=%d sizeof(lapack_int)=%d (ILP64 期望 8/8)\n",
           (int)sizeof(blasint), (int)sizeof(lapack_int));
#ifdef LAPACK_ILP64
    printf("macro LAPACK_ILP64=defined OPENBLAS_USE64BITINT=defined\n\n");
#else
    printf("macro LAPACK_ILP64=undefined OPENBLAS_USE64BITINT=defined\n\n");
#endif

    /* ── ILP64 证明：整型宽度 ─────────────────────────────────────────── */
    {
        int ok = (sizeof(lapack_int) == 8) && (sizeof(blasint) == 8);
        snprintf(buf, sizeof(buf), "sizeof(blasint)=%d sizeof(lapack_int)=%d 期望 8/8",
                 (int)sizeof(blasint), (int)sizeof(lapack_int));
        check(ok, "ILP64: blasint/lapack_int 为 64 位", buf);
    }

    /* ── BLAS：ddot 点积 ──────────────────────────────────────────────── */
    {
        double x[4] = {1.0, 2.0, 3.0, 4.0};
        double y[4] = {5.0, 6.0, 7.0, 8.0};
        blasint n = 4, inc = 1;
        double d = cblas_ddot(n, x, inc, y, inc);   /* 5+12+21+32 = 70 */
        snprintf(buf, sizeof(buf), "ddot=%.1f 期望 70.0", d);
        check(close_to(d, 70.0), "BLAS: cblas_ddot 点积", buf);
    }

    /* ── BLAS：dgemm 矩阵乘 C = A*B ──────────────────────────────────── */
    {
        /* A = [1 2; 3 4]  B = [5 6; 7 8]  →  C = [19 22; 43 50] */
        double A[4] = {1, 2, 3, 4};
        double B[4] = {5, 6, 7, 8};
        double C[4] = {0, 0, 0, 0};
        blasint m = 2, n = 2, k = 2, lda = 2, ldb = 2, ldc = 2;
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                    m, n, k, 1.0, A, lda, B, ldb, 0.0, C, ldc);
        int ok = close_to(C[0], 19) && close_to(C[1], 22) &&
                 close_to(C[2], 43) && close_to(C[3], 50);
        snprintf(buf, sizeof(buf), "C=[%.0f %.0f; %.0f %.0f] 期望 [19 22; 43 50]",
                 C[0], C[1], C[2], C[3]);
        check(ok, "BLAS: cblas_dgemm 矩阵乘", buf);
    }

    /* ── LAPACK：LAPACK_dgesv 解线性方程组 Ax=b ──────────────────────── */
    {
        /* 列主序。A = [2 1; 1 3]，b = [3; 5]  →  x = [0.8; 1.4] */
        lapack_int n = 2, nrhs = 1, lda = 2, ldb = 2, info = 0, ipiv[2];
        double A[4] = {2.0, 1.0, 1.0, 3.0};
        double b[2] = {3.0, 5.0};
        LAPACK_dgesv(&n, &nrhs, A, &lda, ipiv, b, &ldb, &info);
        int ok = (info == 0) && close_to(b[0], 0.8) && close_to(b[1], 1.4);
        snprintf(buf, sizeof(buf), "info=%d x=[%.4f %.4f] 期望 [0.8000 1.4000]",
                 (int)info, b[0], b[1]);
        check(ok, "LAPACK: dgesv_ 解线性方程组", buf);
    }

    /* ── LAPACK：LAPACK_dpotrf Cholesky 分解 ─────────────────────────── */
    {
        /* A = [4 2; 2 5]（正定）→ 下三角 L = [2 0; 1 2] */
        lapack_int n = 2, lda = 2, info = 0;
        char uplo = 'L';
        double A[4] = {4.0, 2.0, 2.0, 5.0};
        LAPACK_dpotrf(&uplo, &n, A, &lda, &info);
        int ok = (info == 0) && close_to(A[0], 2.0) && close_to(A[1], 1.0) &&
                 close_to(A[3], 2.0);
        snprintf(buf, sizeof(buf), "info=%d L=[%.1f 0; %.1f %.1f] 期望 [2 0; 1 2]",
                 (int)info, A[0], A[1], A[3]);
        check(ok, "LAPACK: dpotrf_ Cholesky 分解", buf);
    }

    /* ── LAPACKE：LAPACKE_dgesv 解线性方程组（C 接口）────────────────── */
    {
        /* 列主序 LAPACK_COL_MAJOR。A = [2 1; 1 3]，b = [3; 5] → x = [0.8; 1.4] */
        lapack_int n = 2, nrhs = 1, lda = 2, ldb = 2, info = 0, ipiv[2];
        double A[4] = {2.0, 1.0, 1.0, 3.0};
        double b[2] = {3.0, 5.0};
        info = LAPACKE_dgesv(LAPACK_COL_MAJOR, n, nrhs, A, lda, ipiv, b, ldb);
        int ok = (info == 0) && close_to(b[0], 0.8) && close_to(b[1], 1.4);
        snprintf(buf, sizeof(buf), "info=%d x=[%.4f %.4f] 期望 [0.8000 1.4000]",
                 (int)info, b[0], b[1]);
        check(ok, "LAPACKE: LAPACKE_dgesv 解线性方程组", buf);
    }

    /* ── 配置串核对 ─────────────────────────────────────────────────── */
    {
        int ok = (cfg != NULL) && (strstr(cfg, "0.3.34") != NULL);
        check(ok, "config 串含版本 0.3.34", cfg ? cfg : "(null)");
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
