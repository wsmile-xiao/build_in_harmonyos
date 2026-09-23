/* fakeblas_lp64.c — controlled LP64 BLAS backend for libblastrampoline tests
 *
 * Exports only LP64-mangled symbols (trailing underscore, 32-bit integers).
 * The interface autodetection probe isamax_ reads N as 32-bit int, so LBT
 * classifies this library as LBT_INTERFACE_LP64 with suffix "".
 *
 * All results are deterministic so the test can assert exact values.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static char last_call[64] = "";
static int call_count = 0;

void get_last_call(char *buf, int n) { strncpy(buf, last_call, n - 1); buf[n - 1] = 0; }
int  get_call_count(void)            { return call_count; }
void reset_calls(void)               { call_count = 0; last_call[0] = 0; }
static void record(const char *name) { call_count++; snprintf(last_call, sizeof last_call, "%s", name); }

/* isamax_: N is 32-bit here. The probe passes a 64-bit pattern whose low
 * 32 bits read as 3, so a correct LP64 implementation returns index 2. */
int32_t isamax_(int32_t *n, float *x, int32_t *incx) {
    record("isamax_");
    if (*n < 3) return 0;
    int32_t best = 0;
    for (int32_t i = 0; i < *n && i < 8; i++)
        if (x[i * (*incx)] > x[best * (*incx)]) best = i;
    return best + 1; /* Fortran 1-based */
}

/* sdot_ must return 0.25 for the f2c probe (0.5*0.5) via float return */
float sdot_(int32_t *n, float *x, int32_t *incx, float *y, int32_t *incy) {
    record("sdot_");
    float acc = 0.0f;
    for (int32_t i = 0; i < *n; i++) acc += x[i * (*incx)] * y[i * (*incy)];
    return acc;
}

/* zdotc_/cdotc_ must return 0+0i for zero-length input via normal return */
typedef struct { double re, im; } zcomplex;
zcomplex zdotc_(int32_t *n, double _Complex *x, int32_t *incx,
                double _Complex *y, int32_t *incy) {
    record("zdotc_");
    zcomplex r = {0.0, 0.0};
    (void)n; (void)x; (void)incx; (void)y; (void)incy;
    return r;
}
typedef struct { float re, im; } ccomplex;
ccomplex cdotc_(int32_t *n, float _Complex *x, int32_t *incx,
                float _Complex *y, int32_t *incy) {
    record("cdotc_");
    ccomplex r = {0.0f, 0.0f};
    (void)n; (void)x; (void)incx; (void)y; (void)incy;
    return r;
}

/* deterministic dgemm_: every element of C := alpha*k*m + beta*C_old */
void dgemm_(char *transa, char *transb, int32_t *m, int32_t *n, int32_t *k,
            double *alpha, double *A, int32_t *lda, double *B, int32_t *ldb,
            double *beta, double *C, int32_t *ldc) {
    record("dgemm_");
    (void)transa; (void)transb; (void)A; (void)lda; (void)B; (void)ldb; (void)ldc;
    double fill = (*alpha) * (double)((*k) * (*m));
    int32_t total = (*m) * (*n);
    for (int32_t i = 0; i < total; i++) C[i] = fill + (*beta) * C[i];
}

void daxpy_(int32_t *n, double *da, double *dx, int32_t *incx, double *dy, int32_t *incy) {
    record("daxpy_");
    for (int32_t i = 0; i < *n; i++) dy[i * (*incy)] += (*da) * dx[i * (*incx)];
}

void lsame_(char *ca, char *cb, int32_t *ret) { record("lsame_"); *ret = (*ca == *cb) ? 1 : 0; }
