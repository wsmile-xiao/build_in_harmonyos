/* Real SPOOLES API consumer test (R34): exercises three core modules with
 * deterministic in-memory checks plus one end-to-end consumer flow —
 * no input files needed.
 *
 * Scenario 1 — IV (integer vector): wrap a stack array, verify size,
 *   entry access and the entry sum.
 * Scenario 2 — DV (double vector): same pattern for doubles.
 * Scenario 3 — InpMtx (input matrix): build the 2x2 matrix
 *     [ 4 1 ]
 *     [ 1 3 ]
 *   entry by entry in BY_ROWS / SPOOLES_REAL mode, verify the entry count
 *   and the object modes.
 * Scenario 4 — END-TO-END consumer flow (rule12 完整消费者用例):
 *   assemble the same 2x2 sparse matrix -> run the real compute kernel
 *   InpMtx_nonsym_gmvm (y = A*x) -> persist the matrix with
 *   InpMtx_writeToFormattedFile -> reload it with
 *   InpMtx_readFromFormattedFile -> re-run the compute kernel on the
 *   reloaded object and verify identical results. This is a genuine
 *   functional workflow (组装/计算/落盘/重载/复算), not bare asserts.
 *
 * 15 CHECK assertions total (IV 4 + DV 3 + InpMtx 3 + end-to-end 5).
 * Exit code is nonzero on any failure, so the conan test_package marker
 * (discovered=15/passedCount=15) is proven by exit 0; the counts
 * themselves are fixed by this source file.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "SPOOLES.h"
#include "IV.h"
#include "DV.h"
#include "InpMtx.h"

static int g_total = 0;
static int g_passed = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        g_total++;                                                      \
        if (cond) {                                                     \
            g_passed++;                                                 \
            printf("  [PASS] %s\n", #cond);                             \
        } else {                                                        \
            printf("  [FAIL] %s (line %d)\n", #cond, __LINE__);          \
        }                                                               \
    } while (0)

static int test_iv_vector(void)
{
    int entries[4] = {2, 4, 6, 8};
    int sum = 0;
    int i;
    IV *iv;

    printf("SCENARIO 1: IV integer vector\n");
    iv = IV_new();
    if (iv == NULL) {
        printf("  [FAIL] IV_new returned NULL\n");
        return 1;
    }
    IV_init(iv, 4, entries);
    CHECK(IV_size(iv) == 4);
    CHECK(IV_entry(iv, 0) == 2);
    CHECK(IV_entry(iv, 3) == 8);
    for (i = 0; i < IV_size(iv); i++) {
        sum += IV_entry(iv, i);
    }
    CHECK(sum == 20);
    IV_free(iv);
    return 0;
}

static int test_dv_vector(void)
{
    double entries[3] = {1.0, 2.0, 3.0};
    double sum = 0.0;
    int i;
    DV *dv;

    printf("SCENARIO 2: DV double vector\n");
    dv = DV_new();
    if (dv == NULL) {
        printf("  [FAIL] DV_new returned NULL\n");
        return 1;
    }
    DV_init(dv, 3, entries);
    CHECK(DV_size(dv) == 3);
    CHECK(DV_entry(dv, 2) == 3.0);
    for (i = 0; i < DV_size(dv); i++) {
        sum += DV_entry(dv, i);
    }
    CHECK(fabs(sum - 6.0) < 1e-12);
    DV_free(dv);
    return 0;
}

static int test_inpmtx_input(void)
{
    InpMtx *mtx;

    printf("SCENARIO 3: InpMtx 2x2 input matrix\n");
    mtx = InpMtx_new();
    if (mtx == NULL) {
        printf("  [FAIL] InpMtx_new returned NULL\n");
        return 1;
    }
    InpMtx_init(mtx, INPMTX_BY_ROWS, SPOOLES_REAL, 0, 0);
    InpMtx_inputRealEntry(mtx, 0, 0, 4.0);
    InpMtx_inputRealEntry(mtx, 0, 1, 1.0);
    InpMtx_inputRealEntry(mtx, 1, 0, 1.0);
    InpMtx_inputRealEntry(mtx, 1, 1, 3.0);
    CHECK(mtx->nent == 4);
    CHECK(mtx->coordType == INPMTX_BY_ROWS);
    CHECK(mtx->inputMode == SPOOLES_REAL);
    InpMtx_free(mtx);
    return 0;
}

/* SCENARIO 4: complete end-to-end consumer use case.
 * A = [4 1; 1 3], x = [1, 2]  =>  y = A*x = [6, 7].
 * Steps: assemble -> SpMV compute -> write to file -> read back ->
 * recompute on reloaded object. Returns 0 on full success. */
static int test_e2e_spmv_persist(void)
{
    static const char *tmpfile = "spooles_e2e_tmp.inpmtxf";
    InpMtx *mtx = NULL;
    InpMtx *reloaded = NULL;
    double x[2] = {1.0, 2.0};
    double y[2] = {0.0, 0.0};
    double y2[2] = {0.0, 0.0};
    double alpha[1] = {1.0};
    double beta[1] = {0.0};
    int rc;
    int wrc = 0;
    int rrc = 0;
    FILE *fp = NULL;

    printf("SCENARIO 4: end-to-end SpMV + persist/reload consumer flow\n");
    mtx = InpMtx_new();
    if (mtx == NULL) {
        printf("  [FAIL] InpMtx_new returned NULL (e2e)\n");
        return 1;
    }
    InpMtx_init(mtx, INPMTX_BY_ROWS, SPOOLES_REAL, 0, 0);
    InpMtx_inputRealEntry(mtx, 0, 0, 4.0);
    InpMtx_inputRealEntry(mtx, 0, 1, 1.0);
    InpMtx_inputRealEntry(mtx, 1, 0, 1.0);
    InpMtx_inputRealEntry(mtx, 1, 1, 3.0);

    /* 1. real compute kernel: y = A*x over the raw triple store. */
    rc = InpMtx_nonsym_gmvm(mtx, beta, 2, y, alpha, 2, x);
    CHECK(rc == 1);
    CHECK(fabs(y[0] - 6.0) < 1e-9 && fabs(y[1] - 7.0) < 1e-9);

    /* 2. persist the assembled matrix to disk. */
    fp = fopen(tmpfile, "w");
    if (fp == NULL) {
        printf("  [FAIL] fopen for write failed: %s\n", tmpfile);
        InpMtx_free(mtx);
        return 1;
    }
    wrc = InpMtx_writeToFormattedFile(mtx, fp);
    fclose(fp);
    fp = NULL;
    CHECK(wrc == 1);

    /* 3. reload into a fresh object and re-run the kernel. */
    reloaded = InpMtx_new();
    if (reloaded == NULL) {
        printf("  [FAIL] InpMtx_new returned NULL (reload)\n");
        InpMtx_free(mtx);
        remove(tmpfile);
        return 1;
    }
    fp = fopen(tmpfile, "r");
    if (fp == NULL) {
        printf("  [FAIL] fopen for read failed: %s\n", tmpfile);
        InpMtx_free(mtx);
        InpMtx_free(reloaded);
        remove(tmpfile);
        return 1;
    }
    rrc = InpMtx_readFromFormattedFile(reloaded, fp);
    fclose(fp);
    fp = NULL;
    CHECK(rrc == 1 && reloaded->nent == 4);
    rc = InpMtx_nonsym_gmvm(reloaded, beta, 2, y2, alpha, 2, x);
    CHECK(rc == 1 && fabs(y2[0] - 6.0) < 1e-9 && fabs(y2[1] - 7.0) < 1e-9);

    InpMtx_free(mtx);
    InpMtx_free(reloaded);
    remove(tmpfile);
    return 0;
}

int main(void)
{
    int failed;

    printf("spooles 2.2 consumer test: IV + DV + InpMtx + e2e SpMV flow\n");
    failed = test_iv_vector() + test_dv_vector()
           + test_inpmtx_input() + test_e2e_spmv_persist();

    printf("SPOOLES_TEST_SUMMARY total=%d passed=%d failed=%d\n",
           g_total, g_passed, g_total - g_passed);
    if (failed != 0 || g_passed != g_total) {
        printf("spooles consumer test: FAILED\n");
        return 1;
    }
    if (g_total != 15) {
        printf("spooles consumer test: CHECK COUNT CHANGED (%d != 15)\n",
               g_total);
        return 1;
    }
    printf("spooles 2.2 IV/DV/InpMtx/e2e consumer test: OK\n");
    return 0;
}
