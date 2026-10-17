/* OpenBLAS 0.3.28 鸿蒙 PC 适配验证。
 *
 * R34：不做「dlopen + dlsym 看指针非空」的空壳探测——那只证明符号存在，不证明能算对。
 * 本文件直接 #include OpenBLAS 公共头、直接链接 libopenblas，并对每类能力做**真实数值计算
 * 且校验结果**：
 *   · BLAS   cblas_ddot / cblas_dgemm        —— C 接口
 *   · LAPACK dgesv_ / dpotrf_ / dgeev_       —— Fortran 接口
 *
 * 为什么重点压 LAPACK：本仓此前的 0.3.28 配方用 NOFORTRAN=ON + C_LAPACK=ON（f2c 翻译版，
 * 导出符号比真 Fortran 版少约 1300 个）。本版改用 flang 真 Fortran LAPACK，
 * dgeev_（非对称特征值）会走到大量 Fortran 代码路径，是该改动是否真正生效的硬证据。
 */
#include <cblas.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

/* LAPACK Fortran 接口（OpenBLAS 按 GFORT 约定导出，符号名带下划线后缀） */
extern void dgesv_(int *n, int *nrhs, double *a, int *lda, int *ipiv,
                   double *b, int *ldb, int *info);
extern void dpotrf_(char *uplo, int *n, double *a, int *lda, int *info);
extern void dgeev_(char *jobvl, char *jobvr, int *n, double *a, int *lda,
                   double *wr, double *wi, double *vl, int *ldvl,
                   double *vr, int *ldvr, double *work, int *lwork, int *info);
extern char *openblas_get_config(void);
extern int openblas_get_num_threads(void);

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
    char buf[320];
    const char *cfg = openblas_get_config();
    printf("OpenBLAS config: %s\n", cfg ? cfg : "(null)");
    printf("threads: %d\n\n", openblas_get_num_threads());

    /* ── BLAS：ddot 点积 ───────────────────────────────────────────────── */
    {
        double x[4] = {1.0, 2.0, 3.0, 4.0};
        double y[4] = {5.0, 6.0, 7.0, 8.0};
        double d = cblas_ddot(4, x, 1, y, 1);        /* 5+12+21+32 = 70 */
        snprintf(buf, sizeof(buf), "ddot=%.1f 期望 70.0", d);
        check(close_to(d, 70.0), "BLAS: cblas_ddot 点积", buf);
    }

    /* ── BLAS：dgemm 矩阵乘 C = A*B ────────────────────────────────────── */
    {
        /* A = [1 2; 3 4]  B = [5 6; 7 8]  →  C = [19 22; 43 50] */
        double A[4] = {1, 2, 3, 4};
        double B[4] = {5, 6, 7, 8};
        double C[4] = {0, 0, 0, 0};
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                    2, 2, 2, 1.0, A, 2, B, 2, 0.0, C, 2);
        int ok = close_to(C[0], 19) && close_to(C[1], 22) &&
                 close_to(C[2], 43) && close_to(C[3], 50);
        snprintf(buf, sizeof(buf), "C=[%.0f %.0f; %.0f %.0f] 期望 [19 22; 43 50]",
                 C[0], C[1], C[2], C[3]);
        check(ok, "BLAS: cblas_dgemm 矩阵乘", buf);
    }

    /* ── LAPACK：dgesv_ 解线性方程组 Ax=b ──────────────────────────────── */
    {
        /* 列主序。A = [2 1; 1 3]，b = [3; 5]  →  x = [0.8; 1.4] */
        int n = 2, nrhs = 1, lda = 2, ldb = 2, info = 0, ipiv[2];
        double A[4] = {2.0, 1.0, 1.0, 3.0};
        double b[2] = {3.0, 5.0};
        dgesv_(&n, &nrhs, A, &lda, ipiv, b, &ldb, &info);
        int ok = (info == 0) && close_to(b[0], 0.8) && close_to(b[1], 1.4);
        snprintf(buf, sizeof(buf), "info=%d x=[%.4f %.4f] 期望 [0.8000 1.4000]",
                 info, b[0], b[1]);
        check(ok, "LAPACK: dgesv_ 解线性方程组", buf);
    }

    /* ── LAPACK：dpotrf_ Cholesky 分解 ─────────────────────────────────── */
    {
        /* A = [4 2; 2 5]（正定）→ 下三角 L = [2 0; 1 2] */
        int n = 2, lda = 2, info = 0;
        char uplo = 'L';
        double A[4] = {4.0, 2.0, 2.0, 5.0};
        dpotrf_(&uplo, &n, A, &lda, &info);
        int ok = (info == 0) && close_to(A[0], 2.0) && close_to(A[1], 1.0) &&
                 close_to(A[3], 2.0);
        snprintf(buf, sizeof(buf), "info=%d L=[%.1f 0; %.1f %.1f] 期望 [2 0; 1 2]",
                 info, A[0], A[1], A[3]);
        check(ok, "LAPACK: dpotrf_ Cholesky 分解", buf);
    }

    /* ── LAPACK：dgeev_ 非对称特征值（重量级 Fortran 路径）─────────────── */
    {
        /* A = [2 0; 0 3] 的特征值应为 {2, 3}，虚部为 0 */
        int n = 2, lda = 2, ldvl = 1, ldvr = 1, lwork = 128, info = 0;
        char jobvl = 'N', jobvr = 'N';
        double A[4] = {2.0, 0.0, 0.0, 3.0};
        double wr[2] = {0, 0}, wi[2] = {0, 0};
        double vl[1] = {0}, vr[1] = {0}, work[128];
        dgeev_(&jobvl, &jobvr, &n, A, &lda, wr, wi, vl, &ldvl, vr, &ldvr,
               work, &lwork, &info);
        double lo = wr[0] < wr[1] ? wr[0] : wr[1];
        double hi = wr[0] < wr[1] ? wr[1] : wr[0];
        int ok = (info == 0) && close_to(lo, 2.0) && close_to(hi, 3.0) &&
                 fabs(wi[0]) < 1e-9 && fabs(wi[1]) < 1e-9;
        snprintf(buf, sizeof(buf), "info=%d 特征值={%.4f, %.4f} 期望 {2, 3}",
                 info, lo, hi);
        check(ok, "LAPACK: dgeev_ 非对称特征值", buf);
    }

    /* ── 配置串核对 ───────────────────────────────────────────────────── */
    {
        int ok = (cfg != NULL) && (strstr(cfg, "0.3.28") != NULL);
        check(ok, "config 串含版本 0.3.28", cfg ? cfg : "(null)");
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
