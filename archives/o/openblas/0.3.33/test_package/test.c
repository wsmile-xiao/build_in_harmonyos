/* OpenBLAS 0.3.33 鸿蒙 PC 适配验证。
 *
 * R34：不做「dlopen + dlsym 看指针非空」的空壳探测——那只证明符号存在，不证明能算对。
 * 本文件直接 #include OpenBLAS 公共头（cblas.h/lapacke.h）、直接链接 libopenblas，
 * 并对每类能力做**真实数值计算且校验结果**：
 *   · BLAS    cblas_dgemm                     —— C 接口（NOFORTRAN=1 主路径）
 *   · LAPACK  dgesv_ / dpotrf_                —— Fortran 接口（f2c 转换版，GFORT 命名）
 *   · LAPACKE LAPACKE_dgesv                   —— C 接口（需要 lapacke.h）
 *   · 版本串  openblas_get_config() 含 "0.3.33"
 */
#include <cblas.h>
#include <lapacke.h>
#include <lapack.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

/* LAPACK Fortran 接口：lapack.h 提供 LAPACK_dgesv / LAPACK_dpotrf 宏，展开为
 * 带下划线后缀的 GFORT 符号（dgesv_ / dpotrf_），返回 lapack_int(ILP32=int32)。
 * 勿再手写 extern 声明——lapack.h 已声明，重复声明会类型冲突。 */
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

    /* ── LAPACK：LAPACK_dgesv（= dgesv_）解线性方程组 Ax=b ─────────────── */
    {
        /* 列主序。A = [2 1; 1 3]，b = [3; 5]  →  x = [0.8; 1.4]
         * 注意：lapack.h 中 LAPACK_dgesv 是 Fortran 风格接口，info 通过指针
         * 输出，不依赖返回值赋值。 */
        lapack_int n = 2, nrhs = 1, lda = 2, ldb = 2, info = 0, ipiv[2];
        double A[4] = {2.0, 1.0, 1.0, 3.0};
        double b[2] = {3.0, 5.0};
        LAPACK_dgesv(&n, &nrhs, A, &lda, ipiv, b, &ldb, &info);
        if (info != 0) {
            snprintf(buf, sizeof(buf), "LAPACK_dgesv info=%d != 0",
                     (int)info);
            check(0, "LAPACK: dgesv_ 解线性方程组", buf);
        } else {
            int ok = close_to(b[0], 0.8) && close_to(b[1], 1.4);
            snprintf(buf, sizeof(buf),
                     "info=%d x=[%.4f %.4f] 期望 [0.8000 1.4000]",
                     (int)info, b[0], b[1]);
            check(ok, "LAPACK: dgesv_ 解线性方程组", buf);
        }
    }

    /* ── LAPACK：LAPACK_dpotrf（= dpotrf_）Cholesky 分解 ────────────────── */
    {
        /* A = [4 2; 2 5]（正定）→ 下三角 L = [2 0; 1 2]
         * info 通过指针输出，不依赖返回值赋值。 */
        lapack_int n = 2, lda = 2, info = 0;
        char uplo = 'L';
        double A[4] = {4.0, 2.0, 2.0, 5.0};
        LAPACK_dpotrf(&uplo, &n, A, &lda, &info);
        if (info != 0) {
            snprintf(buf, sizeof(buf), "LAPACK_dpotrf info=%d != 0",
                     (int)info);
            check(0, "LAPACK: dpotrf_ Cholesky 分解", buf);
        } else {
            int ok = close_to(A[0], 2.0) && close_to(A[1], 1.0) &&
                     close_to(A[3], 2.0);
            snprintf(buf, sizeof(buf),
                     "info=%d L=[%.1f 0; %.1f %.1f] 期望 [2 0; 1 2]",
                     (int)info, A[0], A[1], A[3]);
            check(ok, "LAPACK: dpotrf_ Cholesky 分解", buf);
        }
    }

    /* ── LAPACKE：LAPACKE_dgesv 解线性方程组（C 接口）──────────────────── */
    {
        /* 列主序 LAPACK_COL_MAJOR。A = [2 1; 1 3]，b = [3; 5] → x = [0.8; 1.4] */
        int n = 2, nrhs = 1, info = 0, ipiv[2];
        double A[4] = {2.0, 1.0, 1.0, 3.0};
        double b[2] = {3.0, 5.0};
        info = LAPACKE_dgesv(LAPACK_COL_MAJOR, n, nrhs, A, n, ipiv, b, n);
        int ok = (info == 0) && close_to(b[0], 0.8) && close_to(b[1], 1.4);
        snprintf(buf, sizeof(buf), "info=%d x=[%.4f %.4f] 期望 [0.8000 1.4000]",
                 info, b[0], b[1]);
        check(ok, "LAPACKE: LAPACKE_dgesv 解线性方程组", buf);
    }

    /* ── 配置串核对 ───────────────────────────────────────────────────── */
    {
        int ok = (cfg != NULL) && (strstr(cfg, "0.3.33") != NULL);
        check(ok, "config 串含版本 0.3.33", cfg ? cfg : "(null)");
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
