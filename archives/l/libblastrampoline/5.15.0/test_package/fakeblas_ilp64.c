/* fakeblas_ilp64.c — controlled ILP64 BLAS backend for libblastrampoline tests
 *
 * Exports ILP64-mangled symbols (suffix "64_", 64-bit integers), so LBT
 * autodetects suffix "64_" and interface ILP64, and forwards both the
 * LP64-named (dgemm_) and ILP64-named (dgemm_64_) trampolines into it.
 *
 * All results are deterministic; values differ from the LP64 backend so
 * the test can distinguish which backend a call landed in.
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

/* isamax_64_: N is 64-bit. The probe passes 0xffffffff00000003, which reads
 * as negative when interpreted as 64-bit, so a correct ILP64 implementation
 * must return 0. */
int64_t isamax_64_(int64_t *n, float *x, int64_t *incx) {
    record("isamax_64_");
    if (*n < 3) return 0;
    int64_t best = 0;
    for (int64_t i = 0; i < *n && i < 8; i++)
        if (x[i * (*incx)] > x[best * (*incx)]) best = i;
    return best + 1;
}

/* sdot_64_: float return of 0.25 for the f2c probe */
float sdot_64_(int64_t *n, float *x, int64_t *incx, float *y, int64_t *incy) {
    record("sdot_64_");
    float acc = 0.0f;
    for (int64_t i = 0; i < *n; i++) acc += x[i * (*incx)] * y[i * (*incy)];
    return acc;
}

typedef struct { double re, im; } zcomplex;
zcomplex zdotc_64_(int64_t *n, double _Complex *x, int64_t *incx,
                   double _Complex *y, int64_t *incy) {
    record("zdotc_64_");
    zcomplex r = {0.0, 0.0};
    (void)n; (void)x; (void)incx; (void)y; (void)incy;
    return r;
}
typedef struct { float re, im; } ccomplex;
ccomplex cdotc_64_(int64_t *n, float _Complex *x, int64_t *incx,
                   float _Complex *y, int64_t *incy) {
    record("cdotc_64_");
    ccomplex r = {0.0f, 0.0f};
    (void)n; (void)x; (void)incx; (void)y; (void)incy;
    return r;
}

/* deterministic dgemm_64_: every element of C := 2*alpha*k*m + beta*C_old
 * (twice the LP64 backend's fill value, to distinguish backends) */
void dgemm_64_(char *transa, char *transb, int64_t *m, int64_t *n, int64_t *k,
               double *alpha, double *A, int64_t *lda, double *B, int64_t *ldb,
               double *beta, double *C, int64_t *ldc) {
    record("dgemm_64_");
    (void)transa; (void)transb; (void)A; (void)lda; (void)B; (void)ldb; (void)ldc;
    double fill = 2.0 * (*alpha) * (double)((*k) * (*m));
    int64_t total = (*m) * (*n);
    for (int64_t i = 0; i < total; i++) C[i] = fill + (*beta) * C[i];
}

void daxpy_64_(int64_t *n, double *da, double *dx, int64_t *incx, double *dy, int64_t *incy) {
    record("daxpy_64_");
    for (int64_t i = 0; i < *n; i++) dy[i * (*incy)] += (*da) * dx[i * (*incx)];
}

void lsame_64_(char *ca, char *cb, int64_t *ret) { record("lsame_64_"); *ret = (*ca == *cb) ? 1 : 0; }
