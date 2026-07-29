/* SuiteSparse 7.8.3 鸿蒙 PC 适配验证。
 *
 * R34：不做 dlopen+dlsym 空壳探测——直接 #include 各子库公共头、直接链接，
 * 并对每个子库做**真实计算且校验结果**：
 *   · suitesparseconfig  版本查询
 *   · amd / colamd       对一个真实稀疏矩阵求填充缩减排序，校验排列是有效置换
 *   · cholmod            Cholesky 分解并解方程，校验解正确（此路径会用到 BLAS）
 *   · umfpack            LU 分解并解非对称方程，校验解正确
 */
#include <amd.h>
#include <colamd.h>
#include <cholmod.h>
#include <umfpack.h>
#include <SuiteSparse_config.h>

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static int g_failed = 0, g_total = 0;
static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}
static int close_to(double a, double b) { return fabs(a - b) < 1e-9; }

int main(void) {
    char buf[256];
    int ver[3];
    SuiteSparse_version(ver);
    printf("SuiteSparse %d.%d.%d\n\n", ver[0], ver[1], ver[2]);
    snprintf(buf, sizeof(buf), "%d.%d.%d", ver[0], ver[1], ver[2]);
    check(ver[0] == 7, "suitesparseconfig: 版本查询", buf);

    /* 5x5 对称正定稀疏矩阵（列压缩，仅下三角用于 cholmod）：
       A = [ 4 1 0 0 0
             1 4 1 0 0
             0 1 4 1 0
             0 0 1 4 1
             0 0 0 1 4 ]  —— 三对角，严格对角占优 → 正定 */
    const int n = 5;
    int Ap[]  = {0, 2, 5, 8, 11, 13};
    int Ai[]  = {0,1, 0,1,2, 1,2,3, 2,3,4, 3,4};
    double Ax[] = {4,1, 1,4,1, 1,4,1, 1,4,1, 1,4};

    /* ── AMD：填充缩减排序 ─────────────────────────────────────────────── */
    {
        int P[5], seen[5];
        int r = amd_order(n, Ap, Ai, P, NULL, NULL);
        memset(seen, 0, sizeof(seen));
        int valid = (r == AMD_OK);
        for (int i = 0; i < n && valid; i++) {
            if (P[i] < 0 || P[i] >= n || seen[P[i]]) valid = 0;
            else seen[P[i]] = 1;
        }
        snprintf(buf, sizeof(buf), "status=%d P=[%d %d %d %d %d]", r, P[0],P[1],P[2],P[3],P[4]);
        check(valid, "amd: amd_order 产出有效置换", buf);
    }

    /* ── COLAMD：列排序 ───────────────────────────────────────────────── */
    {
        /* colamd 会**就地**在 A 数组里做工作区，其长度必须 >= colamd_recommended(nnz,nr,nc)，
           不能只按 nnz 分配（否则越界，colamd 返回失败）。 */
        int Ap2[6], stats[COLAMD_STATS];
        const int nnz = 13;
        size_t alen = colamd_recommended(nnz, n, n);
        int *Ai2 = (int *)calloc(alen ? alen : 1, sizeof(int));
        memcpy(Ap2, Ap, sizeof(Ap));
        memcpy(Ai2, Ai, nnz * sizeof(int));
        int r = (alen > 0 && Ai2) ? colamd(n, n, (int)alen, Ai2, Ap2, NULL, stats) : 0;
        /* 成功时 Ap2 前 n+1 项给出列的新次序，应是 0..n-1 的一个有效排列 */
        int valid = r;
        int seen[5] = {0};
        for (int i = 0; i < n && valid; i++) {
            if (Ap2[i] < 0 || Ap2[i] >= n || seen[Ap2[i]]) valid = 0;
            else seen[Ap2[i]] = 1;
        }
        snprintf(buf, sizeof(buf), "recommended=%zu ret=%d 列序=[%d %d %d %d %d]",
                 alen, r, Ap2[0], Ap2[1], Ap2[2], Ap2[3], Ap2[4]);
        check(valid, "colamd: 列排序产出有效排列", buf);
        free(Ai2);
    }

    /* ── CHOLMOD：Cholesky 解 Ax=b，校验解 ─────────────────────────────── */
    {
        cholmod_common c;
        cholmod_start(&c);
        cholmod_sparse *A = cholmod_allocate_sparse(n, n, 13, 1, 1, 1, CHOLMOD_REAL, &c);
        int *App = (int*)A->p; int *Aii = (int*)A->i; double *Axx = (double*)A->x;
        /* 只存下三角（stype=1 表示对称、用上三角；这里用 -1 语义更直观：改存上三角） */
        A->stype = 1;
        int nz = 0; App[0] = 0;
        for (int j = 0; j < n; j++) {
            for (int k = Ap[j]; k < Ap[j+1]; k++)
                if (Ai[k] <= j) { Aii[nz] = Ai[k]; Axx[nz] = Ax[k]; nz++; }
            App[j+1] = nz;
        }
        cholmod_dense *b = cholmod_ones(n, 1, CHOLMOD_REAL, &c);
        cholmod_factor *L = cholmod_analyze(A, &c);
        int okfac = cholmod_factorize(A, L, &c);
        cholmod_dense *x = okfac ? cholmod_solve(CHOLMOD_A, L, b, &c) : NULL;
        int ok = 0;
        if (x) {
            /* 校验 A*x ≈ b：用 cholmod 的 sdmult 算残差 */
            cholmod_dense *r = cholmod_copy_dense(b, &c);
            double alpha[2] = {-1, 0}, beta[2] = {1, 0};
            cholmod_sdmult(A, 0, alpha, beta, x, r, &c);
            double *rx = (double*)r->x, nrm = 0;
            for (int i = 0; i < n; i++) nrm += rx[i]*rx[i];
            nrm = sqrt(nrm);
            snprintf(buf, sizeof(buf), "‖Ax-b‖=%.2e", nrm);
            ok = nrm < 1e-10;
            cholmod_free_dense(&r, &c);
        } else {
            snprintf(buf, sizeof(buf), "factorize/solve 失败");
        }
        check(ok, "cholmod: Cholesky 分解并解方程", buf);
        if (x) cholmod_free_dense(&x, &c);
        cholmod_free_factor(&L, &c);
        cholmod_free_dense(&b, &c);
        cholmod_free_sparse(&A, &c);
        cholmod_finish(&c);
    }

    /* ── UMFPACK：LU 解非对称方程，校验解精确 ──────────────────────────── */
    {
        /* 2x2: [2 1; 1 3] x = [3; 5]  →  x = [0.8; 1.4] */
        int Bp[] = {0, 2, 4};
        int Bi[] = {0, 1, 0, 1};
        double Bx[] = {2, 1, 1, 3};
        double bb[] = {3, 5}, xx[2] = {0, 0};
        void *Sym = NULL, *Num = NULL;
        int s1 = umfpack_di_symbolic(2, 2, Bp, Bi, Bx, &Sym, NULL, NULL);
        int s2 = (s1 == UMFPACK_OK) ? umfpack_di_numeric(Bp, Bi, Bx, Sym, &Num, NULL, NULL) : -1;
        int s3 = (s2 == UMFPACK_OK)
                 ? umfpack_di_solve(UMFPACK_A, Bp, Bi, Bx, xx, bb, Num, NULL, NULL) : -1;
        int ok = (s3 == UMFPACK_OK) && close_to(xx[0], 0.8) && close_to(xx[1], 1.4);
        snprintf(buf, sizeof(buf), "status=%d x=[%.4f %.4f] 期望 [0.8000 1.4000]", s3, xx[0], xx[1]);
        check(ok, "umfpack: LU 分解并解方程", buf);
        if (Num) umfpack_di_free_numeric(&Num);
        if (Sym) umfpack_di_free_symbolic(&Sym);
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
