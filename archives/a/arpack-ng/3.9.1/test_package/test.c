/*
 * Test program for arpack-ng: solve a simple symmetric eigenvalue problem.
 * Calls dsaupd_c / dseupd_c (ICB C bindings) to find the 3 largest
 * eigenvalues of a diagonal matrix diag(10, 9, 8, ..., 2, 1).
 * Expected eigenvalues (LM): 10, 9, 8.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "arpack.h"

/* Matrix-vector product: y = A*x where A = diag(10,9,...,1) */
static void dMatVec(const double *x, double *y, int n) {
    int i;
    for (i = 0; i < n; ++i)
        y[i] = ((double)(n - i)) * x[i];
}

int main(void) {
    const int N      = 10;
    const int nev    = 3;
    const int ncv    = 2 * nev + 1;
    const int ldv    = N;
    const int ldz    = N;
    const int lworkl = ncv * (ncv + 8);
    const int rvec   = 1;

    const double tol   = 1e-6;
    const double sigma = 0.0;

    double resid[N];
    double V[ldv * ncv];
    double z[ldz * nev];
    double d[nev];
    double workd[3 * N];
    double workl[lworkl];
    a_int select[ncv];

    a_int iparam[11], ipntr[11];
    iparam[0] = 1;      /* ishift */
    iparam[2] = 10 * N; /* maxit */
    iparam[3] = 1;      /* NB */
    iparam[6] = 1;      /* mode 1: regular */

    char bmat[]   = "I";
    char which[]  = "LM";
    char howmny[] = "A";

    a_int info = 0, ido = 0;
    int i;

    memset(resid, 0, sizeof(resid));
    memset(V, 0, sizeof(V));
    memset(workd, 0, sizeof(workd));
    memset(workl, 0, sizeof(workl));

    /* Reverse communication loop */
    do {
        dsaupd_c(&ido, bmat, (a_int)N, which, (a_int)nev, tol, resid,
                 (a_int)ncv, V, (a_int)ldv, iparam, ipntr,
                 workd, workl, (a_int)lworkl, &info);

        if (ido == 1 || ido == -1) {
            dMatVec(&workd[ipntr[0] - 1], &workd[ipntr[1] - 1], N);
        }
    } while (ido == 1 || ido == -1);

    if (info < 0 || iparam[4] < nev) {
        fprintf(stderr, "Error in dsaupd_c: info=%d, ev found=%d, nev=%d\n",
                (int)info, (int)iparam[4], nev);
        return 1;
    }

    /* Extract eigenvalues */
    dseupd_c((a_int)rvec, howmny, select, d, z, (a_int)ldz, sigma,
             bmat, (a_int)N, which, (a_int)nev, tol, resid,
             (a_int)ncv, V, (a_int)ldv, iparam, ipntr,
             workd, workl, (a_int)lworkl, &info);

    if (info < 0) {
        fprintf(stderr, "Error in dseupd_c: info=%d\n", (int)info);
        return 1;
    }

    /* Verify eigenvalues: dseupd_c returns them in ascending order (8, 9, 10) */
    double expected[3] = {8.0, 9.0, 10.0};
    int ok = 1;
    for (i = 0; i < nev; ++i) {
        double eps = fabs(d[i] - expected[i]);
        printf("Eigenvalue %d: %.6f (expected %.1f, eps=%.2e)\n",
               i, d[i], expected[i], eps);
        if (eps > 1e-5)
            ok = 0;
    }

    if (ok) {
        printf("All eigenvalues verified OK\n");
        return 0;
    } else {
        fprintf(stderr, "Eigenvalue verification FAILED\n");
        return 1;
    }
}
