/**
 * @file test_pastix_solve.c
 *
 * @brief 消费者视角 E2E：用已安装的 PASTIX::pastix 求解 2D 拉普拉斯稀疏系统。
 *
 * 流程与上游 example/simple.c 的 check 加强路径一致：
 *   pastixInitParam → pastixInit → spmReadDriver(SpmDriverLaplacian, "d:30:30:1:2")
 *   → spmCheckAndCorrect → pastix_task_analyze → spmNorm/spmScal
 *   → pastix_task_numfact → spmGenRHS(SpmRhsRndX, 已知解) → pastix_task_solve
 *   → pastix_task_refine → spmCheckAxb(与已知解对比 + 残差) → pastixFinalize
 *
 * 输出协议：逐项 CHECK PASS/FAIL、按用例 TEST PASS/FAIL、TEST SUMMARY；
 * 任一项失败 → 退出码 1。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pastix.h>
#include <spm.h>

static int g_checks = 0;
static int g_fails  = 0;

#define CHECK(cond, what)                                      \
    do {                                                       \
        g_checks++;                                            \
        if (cond) {                                            \
            printf("CHECK PASS: %s\n", (what));                \
        } else {                                               \
            g_fails++;                                         \
            printf("CHECK FAIL: %s\n", (what));                \
        }                                                      \
    } while (0)

static void
case_done(const char *name, int fails_before)
{
    if (g_fails == fails_before) {
        printf("TEST PASS: %s\n", name);
    } else {
        printf("TEST FAIL: %s\n", name);
    }
}

int
main(void)
{
    pastix_data_t *pastix_data = NULL;
    pastix_int_t   iparm[IPARM_SIZE];
    double         dparm[DPARM_SIZE];
    spmatrix_t    *spm;
    spmatrix_t     spm_corrected;
    void          *x, *b, *x0;
    size_t         size;
    double         normA;
    int            rc, before, nrhs = 1;

    printf("== test_pastix_solve: PaStiX 6.4.0 消费者 E2E（2D Laplacian d:30:30:1:2）==\n");

    before = g_fails;
    pastixInitParam(iparm, dparm);
    pastixInit(&pastix_data, MPI_COMM_WORLD, iparm, dparm);
    CHECK(pastix_data != NULL, "pastixInit 返回有效句柄");
    case_done("pastix_init", before);

    before = g_fails;
    spm = (spmatrix_t *)malloc(sizeof(spmatrix_t));
    CHECK(spm != NULL, "spmatrix_t 分配");
    /*
     * Laplacian 驱动生成 M = alpha*D - beta*A（D 为度矩阵、A 为邻接矩阵）。
     * alpha=2（本处第 4 个字段，上游全部 Laplacian 用例同款）得到 M = 2D - A，
     * 严格对角占优、非奇异；缺省 alpha=1 生成 M = D - A 的图 Laplacian，
     * 常数向量属于零空间——右端仍相容时解相差任意常数，残差完美但
     * 与生成右端所用 x0 无法逐位吻合，故这里显式给出 alpha=2。
     */
    rc = spmReadDriver(SpmDriverLaplacian, "d:30:30:1:2", spm);
    CHECK(rc == SPM_SUCCESS, "spmReadDriver(SpmDriverLaplacian, d:30:30:1:2) 成功");
    CHECK(spm->nexp == 900, "未知数个数 == 900（30x30）");
    CHECK(spm->flttype == SpmDouble, "浮点类型 == SpmDouble");
    case_done("read_laplacian", before);

    before = g_fails;
    rc = spmCheckAndCorrect(spm, &spm_corrected);
    CHECK(rc >= 0, "spmCheckAndCorrect 无错误返回");
    if (rc != 0) {
        spmExit(spm);
        *spm = spm_corrected;
    }
    case_done("check_and_correct", before);

    before = g_fails;
    pastix_task_analyze(pastix_data, spm);
    normA = spmNorm(SpmFrobeniusNorm, spm);
    CHECK(normA > 0.0, "Frobenius 范数 > 0");
    spmScal(1.0 / normA, spm);
    pastix_task_numfact(pastix_data, spm);
    case_done("analyze_and_numfact", before);

    before = g_fails;
    size = pastix_size_of(spm->flttype) * (size_t)spm->nexp * (size_t)nrhs;
    x  = malloc(size);
    b  = malloc(size);
    x0 = malloc(size);
    CHECK(x != NULL && b != NULL && x0 != NULL, "x/b/x0 向量分配");

    /* 生成已知解 x0 与右端 b = A * x0 */
    spmGenRHS(SpmRhsRndX, nrhs, spm, x0, spm->nexp, b, spm->nexp);
    memcpy(x, b, size);

    pastix_task_solve(pastix_data, spm->nexp, nrhs, x, spm->nexp);
    pastix_task_refine(pastix_data, spm->nexp, nrhs, b, spm->nexp, x, spm->nexp);

    /* 与已知解对比 + 残差校验，成功为 SPM_SUCCESS */
    rc = spmCheckAxb(dparm[DPARM_EPSILON_REFINEMENT], nrhs, spm,
                     x0, spm->nexp, b, spm->nexp, x, spm->nexp);
    CHECK(rc == SPM_SUCCESS, "spmCheckAxb == SPM_SUCCESS（解正确且残差收敛）");
    case_done("solve_and_refine", before);

    before = g_fails;
    spmExit(spm);
    free(spm);
    free(x);
    free(b);
    free(x0);
    pastixFinalize(&pastix_data);
    CHECK(pastix_data == NULL, "pastixFinalize 释放并置空句柄");
    case_done("finalize", before);

    printf("TEST SUMMARY: %d checks, %d failed -> %s\n",
           g_checks, g_fails, (g_fails == 0) ? "ALL PASS" : "FAILURES");
    return (g_fails == 0) ? 0 : 1;
}
