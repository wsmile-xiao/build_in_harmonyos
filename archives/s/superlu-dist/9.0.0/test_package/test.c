/*! \file
 * Consumer test for SuperLU_DIST (OHOS adaptation).
 *
 * Solves a 5x5 sparse tridiagonal system through the library's real
 * distributed API -- pdgssvx_ABglobal() -- and verifies the returned
 * solution against the known exact solution.  This is a genuine API test
 * (R34): it links the packaged library, calls its solver, and asserts on
 * the numerical result.
 *
 *   A x = b  with
 *     A = [ 4 -1  0  0  0        x = [1 2 3 4 5]^T
 *          -1  4 -1  0  0
 *           0 -1  4 -1  0        b = A x = [2 4 6 8 16]^T
 *           0  0 -1  4 -1
 *           0  0  0 -1  4 ]
 *
 * The matrix is assembled in memory in global compressed-sparse-column form
 * (SLU_NC), so the test needs no external data file.
 *
 * NOTE: the arrays handed to the library are allocated with its own
 * intMalloc_dist/doubleMalloc_dist.  Destroy_CompCol_Matrix_dist() calls
 * SUPERLU_FREE on them, so passing stack arrays would free invalid memory
 * (this mirrors EXAMPLE/pddrive_ABglobal.c, which uses dallocateA_dist).
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <mpi.h>
#include "superlu_ddefs.h"

#define N 5
#define NNZ 13            /* 2 + 3 + 3 + 3 + 2 nonzeros */

/* Reference copies of the matrix in CSC form: used both to fill the
 * library-owned arrays and to recompute the residual independently. */
static const int_t xa_ref[N + 1] = {0, 2, 5, 8, 11, 13};
static const int_t asub_ref[NNZ] = {0, 1,
                                    0, 1, 2,
                                    1, 2, 3,
                                    2, 3, 4,
                                    3, 4};
static const double a_ref[NNZ] = {4.0, -1.0,
                                  -1.0, 4.0, -1.0,
                                  -1.0, 4.0, -1.0,
                                  -1.0, 4.0, -1.0,
                                  -1.0, 4.0};
static const double xtrue[N] = {1.0, 2.0, 3.0, 4.0, 5.0};
static const double b_orig[N] = {2.0, 4.0, 6.0, 8.0, 16.0};

int main(int argc, char *argv[])
{
    int i, nprocs, iam, info = 0, ok = 0;
    int nprow, npcol;
    double max_err = 0.0, residual = 0.0;
    int nrhs = 1;                 /* pdgssvx_ABglobal takes int for ldb/nrhs */
    int ldb = N;

    gridinfo_t grid;
    SuperMatrix A;
    superlu_dist_options_t options;
    SuperLUStat_t stat;
    dScalePermstruct_t ScalePermstruct;
    dLUstruct_t LUstruct;
    double berr;
    int_t *xa = NULL, *asub = NULL;
    double *a = NULL, *b = NULL;

    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
    MPI_Comm_rank(MPI_COMM_WORLD, &iam);

    /* A 1 x nprocs process grid: valid for any number of ranks. */
    nprow = 1;
    npcol = nprocs;
    if (nprow * npcol != nprocs) {
        if (iam == 0)
            fprintf(stderr, "cannot factor %d ranks into a %dx? grid\n",
                    nprocs, nprow);
        MPI_Finalize();
        return EXIT_FAILURE;
    }

    superlu_gridinit(MPI_COMM_WORLD, nprow, npcol, &grid);
    if (grid.iam == -1) {
        /* This rank is not part of the grid; nothing to do. */
        superlu_gridexit(&grid);
        MPI_Finalize();
        return EXIT_SUCCESS;
    }

    if (grid.iam == 0) {
        int v_major, v_minor, v_bugfix;
        superlu_dist_GetVersionNumber(&v_major, &v_minor, &v_bugfix);
        printf("SuperLU_DIST version:\t%d.%d.%d\n", v_major, v_minor, v_bugfix);
        printf("Process grid:\t\t%d X %d\n", nprow, npcol);
    }

    /* Assemble A in library-owned heap storage; SLU_NC is global CSC, which
     * pdgssvx_ABglobal distributes internally. */
    xa = intMalloc_dist(N + 1);
    asub = intMalloc_dist(NNZ);
    a = doubleMalloc_dist(NNZ);
    b = doubleMalloc_dist(N);
    if (!xa || !asub || !a || !b) {
        if (iam == 0) fprintf(stderr, "allocation failed\n");
        MPI_Finalize();
        return EXIT_FAILURE;
    }
    memcpy(xa, xa_ref, sizeof(xa_ref));
    memcpy(asub, asub_ref, sizeof(asub_ref));
    memcpy(a, a_ref, sizeof(a_ref));
    memcpy(b, b_orig, sizeof(b_orig));

    dCreate_CompCol_Matrix_dist(&A, N, N, NNZ, a, asub, xa,
                               SLU_NC, SLU_D, SLU_GE);

    set_default_options_dist(&options);
    options.PrintStat = NO;

    dScalePermstructInit(N, N, &ScalePermstruct);
    dLUstructInit(N, &LUstruct);
    PStatInit(&stat);

    pdgssvx_ABglobal(&options, &A, &ScalePermstruct, b, ldb, nrhs, &grid,
                     &LUstruct, &berr, &stat, &info);

    /* b now holds the solution.  Check it against the exact solution and
     * independently recompute the residual ||A x - b_original||inf, using
     * the reference arrays (so this is valid even though the solver may
     * have reallocated its own copies). */
    if (grid.iam == 0) {
        int_t row, col;
        if (info != 0)
            fprintf(stderr, "ERROR: pdgssvx_ABglobal returned info = %d\n", info);
        for (i = 0; i < N; ++i) {
            double err = fabs(b[i] - xtrue[i]);
            if (err > max_err) max_err = err;
        }
        for (row = 0; row < N; ++row) {
            double acc = 0.0, diff;
            for (col = 0; col < N; ++col) {
                int_t k;
                for (k = xa_ref[col]; k < xa_ref[col + 1]; ++k) {
                    if (asub_ref[k] == row) acc += a_ref[k] * b[col];
                }
            }
            diff = fabs(acc - b_orig[row]);
            if (diff > residual) residual = diff;
        }
        printf("solution max error = %.3e\nresidual ||Ax-b||inf = %.3e\n",
               max_err, residual);
    }

    /* Every rank must agree, so rank 0 broadcasts its verdict while MPI is
     * still active (MPI calls after MPI_Finalize are undefined). */
    ok = (info == 0 && max_err < 1e-8 && residual < 1e-8) ? 1 : 0;
    MPI_Bcast(&ok, 1, MPI_INT, 0, MPI_COMM_WORLD);

    /* Release storage.  Destroy_CompCol_Matrix_dist frees xa/asub/a. */
    PStatFree(&stat);
    Destroy_CompCol_Matrix_dist(&A);
    dDestroy_LU(N, &grid, &LUstruct);
    dScalePermstructFree(&ScalePermstruct);
    dLUstructFree(&LUstruct);
    SUPERLU_FREE(b);
    superlu_gridexit(&grid);
    MPI_Finalize();

    if (!ok) {
        if (iam == 0)
            fprintf(stderr, "FAILED: solver did not reproduce the solution "
                            "(max_err=%.3e residual=%.3e info=%d)\n",
                    max_err, residual, info);
        return EXIT_FAILURE;
    }

    if (iam == 0)
        printf("PASSED: SuperLU_DIST solved the system to 1e-8\n");
    return EXIT_SUCCESS;
}
