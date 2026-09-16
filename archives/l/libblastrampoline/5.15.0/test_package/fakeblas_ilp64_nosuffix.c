/* fakeblas_ilp64_nosuffix.c — controlled ILP64 BLAS backend with LP64-style
 * symbol names (no "64_" suffix) for libblastrampoline deepbindless conflict
 * detection tests.
 *
 * On an RTLD_DEEPBIND-less system (musl/OHOS), loading an LP64 BLAS and an
 * unsuffixed ILP64 BLAS together must be REFUSED by libblastrampoline, because
 * both would bind to the same exported trampoline symbols (e.g. dgemm_) with
 * incompatible integer widths. This backend exports isamax_ with 64-bit
 * integer arguments so autodetection classifies it as ILP64 with suffix "".
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

/* isamax_ with 64-bit N: the probe passes 0xffffffff00000003 which is negative
 * when read as 64-bit, so a correct ILP64 implementation returns 0. */
int64_t isamax_(int64_t *n, float *x, int64_t *incx) {
    record("isamax_");
    if (*n < 3) return 0;
    int64_t best = 0;
    for (int64_t i = 0; i < *n && i < 8; i++)
        if (x[i * (*incx)] > x[best * (*incx)]) best = i;
    return best + 1;
}

float sdot_(int64_t *n, float *x, int64_t *incx, float *y, int64_t *incy) {
    record("sdot_");
    float acc = 0.0f;
    for (int64_t i = 0; i < *n; i++) acc += x[i * (*incx)] * y[i * (*incy)];
    return acc;
}

typedef struct { double re, im; } zcomplex;
zcomplex zdotc_(int64_t *n, double _Complex *x, int64_t *incx,
                double _Complex *y, int64_t *incy) {
    record("zdotc_");
    zcomplex r = {0.0, 0.0};
    (void)n; (void)x; (void)incx; (void)y; (void)incy;
    return r;
}
typedef struct { float re, im; } ccomplex;
ccomplex cdotc_(int64_t *n, float _Complex *x, int64_t *incx,
                float _Complex *y, int64_t *incy) {
    record("cdotc_");
    ccomplex r = {0.0f, 0.0f};
    (void)n; (void)x; (void)incx; (void)y; (void)incy;
    return r;
}

void dgemm_(char *transa, char *transb, int64_t *m, int64_t *n, int64_t *k,
            double *alpha, double *A, int64_t *lda, double *B, int64_t *ldb,
            double *beta, double *C, int64_t *ldc) {
    record("dgemm_");
    (void)transa; (void)transb; (void)A; (void)lda; (void)B; (void)ldb; (void)ldc;
    double fill = 2.0 * (*alpha) * (double)((*k) * (*m));
    int64_t total = (*m) * (*n);
    for (int64_t i = 0; i < total; i++) C[i] = fill + (*beta) * C[i];
}

void daxpy_(int64_t *n, double *da, double *dx, int64_t *incx, double *dy, int64_t *incy) {
    record("daxpy_");
    for (int64_t i = 0; i < *n; i++) dy[i * (*incy)] += (*da) * dx[i * (*incx)];
}

void lsame_(char *ca, char *cb, int64_t *ret) { record("lsame_"); *ret = (*ca == *cb) ? 1 : 0; }
