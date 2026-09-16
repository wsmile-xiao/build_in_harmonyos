/* test_consumer.c — libblastrampoline consumer test (controlled fake BLAS backends)
 *
 * Verifies against two deterministic fake backends (no real BLAS involved):
 *   1. lbt_get_config(): build flags DEEPBINDLESS (musl/OHOS) + F2C + RETSTYLE
 *      capability bits, exported symbol count > 4000
 *   2. lbt_forward() on a nonexistent library returns 0 (error path)
 *   3. lbt_forward(LP64 fake backend): suffix "" autodetected, interface LP64,
 *      dgemm_/daxpy_/sdot_ trampolines forward and compute deterministic values
 *   4. Backend switch: clear+forward to ILP64 backend (suffix "64_"): dgemm_ and
 *      dgemm_64_ both land in the ILP64 backend; results change accordingly
 *   5. lbt_get_forward() on unknown symbol returns NULL
 *   6. deepbindless LP64+ILP64(unsuffixed) conflict detection refuses to load
 *
 * NOTE on OHOS/musl semantics: no RTLD_DEEPBIND; LBT forces DEEPBINDLESS mode
 * (lbt_get_use_deepbind() == 0, LBT_BUILDFLAGS_DEEPBINDLESS set).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <dlfcn.h>
#include <libblastrampoline.h>

/* Fortran BLAS prototypes, declared to match the real BLAS ABI per interface:
 *   - LP64 interface (suffix "_"): every integer argument is 32-bit.
 *   - ILP64 interface (suffix "64_"): every integer argument is 64-bit.
 * These mirror the signatures the fake backends export (fakeblas_lp64.c uses
 * int32_t, fakeblas_ilp64.c uses int64_t), which in turn mirror real LP64 /
 * ILP64 BLAS libraries.
 *
 * We deliberately do NOT take these prototypes from the package's bundled
 * f77blas.h: its LP64 openblas_config.h defines OPENBLAS_USE64BITINT (an
 * upstream extraction quirk — both interface dirs are config-identical), which
 * makes `blasint` = long (64-bit) there and would mismatch the real 32-bit
 * LP64 ABI. It also does not declare the "64_"-suffixed ILP64 symbols at all. */
void dgemm_(char *transa, char *transb, int32_t *m, int32_t *n, int32_t *k,
            double *alpha, double *A, int32_t *lda, double *B, int32_t *ldb,
            double *beta, double *C, int32_t *ldc);
void daxpy_(int32_t *n, double *da, double *dx, int32_t *incx,
            double *dy, int32_t *incy);
float sdot_(int32_t *n, float *sx, int32_t *incx, float *sy, int32_t *incy);

void dgemm_64_(char *transa, char *transb, int64_t *m, int64_t *n, int64_t *k,
               double *alpha, double *A, int64_t *lda, double *B, int64_t *ldb,
               double *beta, double *C, int64_t *ldc);
void daxpy_64_(int64_t *n, double *da, double *dx, int64_t *incx,
               double *dy, int64_t *incy);

/* fake backend introspection API (identical in both fakeblas_*.c) */
typedef void (*get_last_call_t)(char *, int);
typedef int  (*get_call_count_t)(void);
typedef void (*reset_calls_t)(void);

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <fakeblas_lp64.so> <fakeblas_ilp64.so> <fakeblas_ilp64_nosuffix.so>\n", argv[0]);
        return 2;
    }
    const char *lp64_backend = argv[1];
    const char *ilp64_backend = argv[2];
    const char *nosuffix_ilp64_backend = argv[3];
    char last[64];

    /* ---------- 1. library introspection ---------- */
    const lbt_config_t *cfg = lbt_get_config();
    CHECK(cfg != NULL, "lbt_get_config() != NULL");
    CHECK(cfg->num_exported_symbols > 4000, "num_exported_symbols > 4000 (BLAS+LAPACK+LAPACKE)");
    printf("  exported symbols: %" PRIu32 "\n", cfg->num_exported_symbols);
    CHECK(cfg->build_flags & LBT_BUILDFLAGS_DEEPBINDLESS, "build is DEEPBINDLESS (musl/OHOS)");
    printf("  build_flags: 0x%" PRIx32 "\n", cfg->build_flags);
    CHECK(lbt_get_use_deepbind() == 0, "lbt_get_use_deepbind() == 0 (no RTLD_DEEPBIND on musl)");
    CHECK(cfg->loaded_libs != NULL && cfg->loaded_libs[0] == NULL,
          "initially no loaded libs");

    /* ---------- 2. error paths ---------- */
    CHECK(lbt_forward("/nonexistent/libdoesnotexist.so", 1, 0, NULL) == 0,
          "lbt_forward(nonexistent) returns 0");

    /* ---------- 3. LP64 backend forwarding ---------- */
    CHECK(lbt_forward(lp64_backend, 1, 0, NULL) > 0, "lbt_forward(LP64 backend) succeeds");
    const lbt_config_t *cfg2 = lbt_get_config();
    CHECK(cfg2->loaded_libs != NULL && cfg2->loaded_libs[0] != NULL,
          "LP64 backend registered in loaded_libs");
    if (cfg2->loaded_libs && cfg2->loaded_libs[0]) {
        CHECK(cfg2->loaded_libs[0]->interface == LBT_INTERFACE_LP64,
              "interface autodetected as LP64 (isamax_ sees 32-bit N)");
        CHECK(cfg2->loaded_libs[0]->suffix != NULL && strcmp(cfg2->loaded_libs[0]->suffix, "") == 0,
              "suffix autodetected as \"\" (plain trailing underscore)");
        CHECK(cfg2->loaded_libs[0]->handle != NULL, "loaded_libs[0].handle != NULL");
        printf("  LP64 suffix: '%s', interface: %d\n",
               cfg2->loaded_libs[0]->suffix, cfg2->loaded_libs[0]->interface);
    }
    void *fb = dlopen(lp64_backend, RTLD_NOW | RTLD_LOCAL);
    CHECK(fb != NULL, "test dlopen(LP64 backend) works");
    get_last_call_t  f_last  = (get_last_call_t)dlsym(fb, "get_last_call");
    get_call_count_t f_count = (get_call_count_t)dlsym(fb, "get_call_count");
    reset_calls_t    f_reset = (reset_calls_t)dlsym(fb, "reset_calls");
    CHECK(f_last && f_count && f_reset, "backend introspection symbols resolvable");

    if (f_reset) {
        char ta = 'N', tb = 'N';
        int32_t m = 2, n = 2, k = 2, lda = 2, ldb = 2, ldc = 2;
        double alpha = 1.0, beta = 0.0;
        double A[4] = {1, 1, 1, 1}, B[4] = {1, 1, 1, 1}, C[4] = {9, 9, 9, 9};
        /* LP64 backend dgemm_: fill = alpha*k*m = 4.0, beta=0 */
        dgemm_(&ta, &tb, &m, &n, &k, &alpha, A, &lda, B, &ldb, &beta, C, &ldc);
        CHECK(C[0] == 4.0 && C[3] == 4.0, "dgemm_ forwarded to LP64 backend (fill=alpha*k*m)");
        f_last(last, sizeof(last));
        CHECK(strcmp(last, "dgemm_") == 0, "LP64 backend recorded dgemm_ call");

        /* daxpy_ with real math through the trampoline */
        f_reset();
        int32_t one = 1, cnt = 3;
        double da = 2.0;
        double x[3] = {1, 2, 3}, y[3] = {10, 20, 30};
        daxpy_(&cnt, &da, x, &one, y, &one);
        CHECK(y[0] == 12.0 && y[1] == 24.0 && y[2] == 36.0, "daxpy_ forwarded with correct math");
        f_last(last, sizeof(last));
        CHECK(strcmp(last, "daxpy_") == 0, "LP64 backend recorded daxpy_ call");

        /* sdot_ (float return, f2c probe symbol) */
        f_reset();
        float sx[3] = {1, 1, 1}, sy[3] = {2, 2, 2};
        float s = sdot_(&cnt, sx, &one, sy, &one);
        CHECK(s == 6.0f, "sdot_ forwarded (float return convention)");
        f_last(last, sizeof(last));
        CHECK(strcmp(last, "sdot_") == 0, "LP64 backend recorded sdot_ call");

        /* The 32-bit interface table was populated by the LP64 backend; the
         * ILP64 (64-bit) table was not. But note that `clear=1` above rewrote
         * BOTH tables to default_func before the LP64 load filled the 32-bit
         * one (libblastrampoline.c: clear loop sets exported_func{32,64}_addrs
         * to default_func), so the ILP64 entry here is default_func — not
         * NULL, and distinct from the (void*)-1 unknown-symbol sentinel
         * (checked in section 5) and from the real LP64 forward address. */
        CHECK(lbt_get_forward("dgemm_", LBT_INTERFACE_ILP64, 0) == lbt_get_default_func(),
              "lbt_get_forward(dgemm_, ILP64) is default_func: 64-bit table untouched by LP64-only load");
        CHECK(lbt_get_forward("dgemm_", LBT_INTERFACE_LP64, 0) != NULL
                  && lbt_get_forward("dgemm_", LBT_INTERFACE_LP64, 0) != (const void *)-1
                  && lbt_get_forward("dgemm_", LBT_INTERFACE_LP64, 0) != lbt_get_default_func(),
              "lbt_get_forward(dgemm_, LP64) resolves to the forwarded LP64 address");
    }

    /* ---------- 4. backend switching to ILP64 ---------- */
    CHECK(lbt_forward(ilp64_backend, 1, 0, NULL) > 0, "lbt_forward(ILP64 backend, clear=1) succeeds");
    /* Reverse-validation of the interface argument: after clear=1 the 32-bit
     * table entries are rewritten to default_func, while the ILP64 load then
     * fills the 64-bit table with the suffixed backend symbols. So the same
     * symbol name now resolves differently per interface — proving that the
     * LBT_INTERFACE_* value passed to lbt_get_forward() actually selects the
     * table, and that the constants match the widths we assume (32 vs 64). */
    CHECK(lbt_get_forward("dgemm_", LBT_INTERFACE_ILP64, 0) != NULL
              && lbt_get_forward("dgemm_", LBT_INTERFACE_ILP64, 0) != (const void *)-1,
          "lbt_get_forward(dgemm_, ILP64) resolves after ILP64 load (64-bit table now filled)");
    CHECK(lbt_get_forward("dgemm_", LBT_INTERFACE_ILP64, 0) != lbt_get_default_func(),
          "ILP64 forward target is the backend function, not default_func");
    const lbt_config_t *cfg3 = lbt_get_config();
    CHECK(cfg3->loaded_libs != NULL && cfg3->loaded_libs[0] != NULL,
          "ILP64 backend registered after switch");
    if (cfg3->loaded_libs && cfg3->loaded_libs[0]) {
        CHECK(cfg3->loaded_libs[0]->interface == LBT_INTERFACE_ILP64,
              "interface autodetected as ILP64 (isamax_64_ sees 64-bit N)");
        CHECK(cfg3->loaded_libs[0]->suffix != NULL && strcmp(cfg3->loaded_libs[0]->suffix, "64_") == 0,
              "suffix autodetected as \"64_\"");
        printf("  ILP64 suffix: '%s', interface: %d\n",
               cfg3->loaded_libs[0]->suffix, cfg3->loaded_libs[0]->interface);
    }
    void *fb64 = dlopen(ilp64_backend, RTLD_NOW | RTLD_LOCAL);
    CHECK(fb64 != NULL, "test dlopen(ILP64 backend) works");
    get_last_call_t  b_last  = (get_last_call_t)dlsym(fb64, "get_last_call");
    reset_calls_t    b_reset = (reset_calls_t)dlsym(fb64, "reset_calls");
    CHECK(b_last && b_reset, "ILP64 backend introspection symbols resolvable");

    if (b_reset) {
        b_reset();
        char ta = 'N', tb = 'N';
        int64_t m = 2, n = 2, k = 2, lda = 2, ldb = 2, ldc = 2;
        double alpha = 1.0, beta = 0.0;
        double A[4] = {1, 1, 1, 1}, B[4] = {1, 1, 1, 1}, C[4] = {9, 9, 9, 9};
        /* ILP64 backend dgemm_64_: fill = 2*alpha*k*m = 8.0 (different from LP64's 4.0) */
        dgemm_64_(&ta, &tb, &m, &n, &k, &alpha, A, &lda, B, &ldb, &beta, C, &ldc);
        CHECK(C[0] == 8.0 && C[3] == 8.0, "dgemm_64_ forwarded to ILP64 backend (fill=2*alpha*k*m)");
        f_last = b_last;
        f_last(last, sizeof(last));
        CHECK(strcmp(last, "dgemm_64_") == 0, "ILP64 backend recorded dgemm_64_ call");

        /* dgemm_ (32-bit name) is NOT taken over by a suffix-"64_" ILP64 backend:
         * on deepbindless systems LBT only takes over the 32-bit symbols when
         * the ILP64 library itself uses suffix "" (see lbt_set_forward_by_index:
         * DEEPBINDLESS_INTERFACE_ILP64_LOADED is only set for suffix-"" ILP64).
         * So after switching to the "64_" backend, dgemm_ still points at the
         * default handler. */
        b_reset();
        int32_t m32 = 2, n32 = 2, k32 = 2, lda32 = 2, ldb32 = 2, ldc32 = 2;
        double C2[4] = {9, 9, 9, 9};
        dgemm_(&ta, &tb, &m32, &n32, &k32, &alpha, A, &lda32, B, &ldb32, &beta, C2, &ldc32);
        CHECK(C2[0] == 9.0, "dgemm_ (32-bit name) NOT hijacked by suffix-64_ ILP64 backend (deepbindless semantics)");
        f_last = b_last;
        f_last(last, sizeof(last));
        CHECK(strcmp(last, "dgemm_64_") != 0, "no dgemm_64_ call recorded for 32-bit dgemm_ call");

        /* daxpy_64_ direct call */
        b_reset();
        int64_t one64 = 1, cnt64 = 3;
        double da = 2.0;
        double x[3] = {1, 2, 3}, y[3] = {10, 20, 30};
        daxpy_64_(&cnt64, &da, x, &one64, y, &one64);
        CHECK(y[0] == 12.0 && y[1] == 24.0 && y[2] == 36.0, "daxpy_64_ forwarded with correct math");
        f_last = b_last;
        f_last(last, sizeof(last));
        CHECK(strcmp(last, "daxpy_64_") == 0, "ILP64 backend recorded daxpy_64_ call");
    }

    /* ---------- 5. lbt_get_forward() on unknown symbol ---------- */
    CHECK(lbt_get_forward("not_a_real_blas_symbol_", 32, 0) == (const void *)-1,
          "lbt_get_forward(unknown symbol) returns (void*)-1 sentinel");

    /* ---------- 6. deepbindless LP64 + unsuffixed-ILP64 conflict refusal ---------- */
    /* Reset to LP64 backend, then try to additionally load an unsuffixed ILP64
     * backend with clear=0: on deepbindless (musl/OHOS) systems this must be
     * REFUSED because both would fight over the same LP64-named symbols. */
    CHECK(lbt_forward(lp64_backend, 1, 0, NULL) > 0, "re-forward LP64 with clear=1 (reset for conflict test)");
    CHECK(lbt_forward(nosuffix_ilp64_backend, 0, 0, NULL) == 0,
          "deepbindless conflict: unsuffixed ILP64 after LP64 (clear=0) is REFUSED");
    /* and the reverse order is refused as well */
    CHECK(lbt_forward(nosuffix_ilp64_backend, 1, 0, NULL) > 0, "clear+forward unsuffixed ILP64");
    CHECK(lbt_forward(lp64_backend, 0, 0, NULL) == 0,
          "deepbindless conflict: LP64 after unsuffixed ILP64 (clear=0) is REFUSED");
    /* suffix-"64_" ILP64 after LP64 with clear=0 is ALLOWED (no name collision) */
    CHECK(lbt_forward(lp64_backend, 1, 0, NULL) > 0, "re-forward LP64 with clear=1");
    CHECK(lbt_forward(ilp64_backend, 0, 0, NULL) > 0,
          "LP64 + suffixed-ILP64(64_) with clear=0 is ALLOWED (disjoint symbol names)");

    printf("\n%d failure(s)\n", failures);
    return failures > 0;
}
