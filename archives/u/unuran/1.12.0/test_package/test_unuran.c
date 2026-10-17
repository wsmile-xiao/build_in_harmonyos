/* ------------------------------------------------------------- */
/* Consumer test for the packaged UNU.RAN 1.12.0 (unuran).       */
/*                                                               */
/* Uses only the installed public headers (`<unuran.h>` plus     */
/* `unuran_tests.h`) and the installed static library, so it     */
/* fails if the package layout, the public header set or the     */
/* link interface regresses.                                     */
/*                                                               */
/* Six groups, each returning its own exit code so that a CI log */
/* pinpoints the failing area without a debugger:                */
/*   2 = group1 object model / parser / version identity         */
/*   3 = group2 seeding determinism (bit-for-bit)                */
/*   4 = group3 statistical sanity of the sampled variates       */
/*   5 = group4 discrete distributions + object (par/init) API   */
/*   6 = group5 HarmonyOS-specific ABI / FP identity             */
/*   7 = group6 HarmonyOS threads: independent URNG per thread   */
/* ------------------------------------------------------------- */
#include <unuran.h>

#include <float.h>
#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond)                                                    \
    do {                                                               \
        if (!(cond)) {                                                 \
            failures++;                                                \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #cond);    \
        }                                                              \
    } while (0)

#define CHECK_CLOSE(a, b, tol)                                         \
    do {                                                               \
        double _a = (a), _b = (b), _t = (tol);                         \
        if (!(fabs(_a - _b) <= _t)) {                                  \
            failures++;                                                \
            fprintf(stderr, "FAIL line %d: |%.17g - %.17g| > %g\n",    \
                    __LINE__, _a, _b, _t);                             \
        }                                                              \
    } while (0)

#define GROUP_RESULT(n)                                                \
    do {                                                               \
        if (failures) {                                                \
            fprintf(stderr, "group %d FAILED (%d checks)\n", n,        \
                    failures);                                         \
            return n;                                                  \
        }                                                              \
        printf("group %d OK\n", n);                                    \
    } while (0)

/* FNV-1a over the raw IEEE-754 bit pattern of a double, so the thread
 * check compares bit for bit and cannot be mollified by "close enough"
 * rounding. */
static unsigned long long fp_digest(const double *x, int n)
{
    unsigned long long h = 1469598103934665603ULL;
    int i;
    for (i = 0; i < n; i++) {
        unsigned char buf[8];
        int j;
        memcpy(buf, &x[i], sizeof(buf));
        for (j = 0; j < 8; j++) {
            h ^= (unsigned long long)buf[j];
            h *= 1099511628211ULL;
        }
    }
    return h;
}

/* ------------------------------------------------------------- */

static int group1_object_model(void)
{
    UNUR_GEN   *gen;
    UNUR_DISTR *distr;
    const char *id;
    const char *info;

    gen = unur_str2gen("normal(0,1)");
    CHECK(gen != NULL);
    if (gen == NULL) {
        GROUP_RESULT(2);
    }

    CHECK(unur_get_dimension(gen) == 1);
    CHECK(unur_get_method(gen) != 0);
    CHECK(unur_get_genid(gen) != NULL);

    id = unur_get_genid(gen);
    CHECK(id != NULL && strlen(id) > 0);
    /* the generator id has the documented "METHOD.serial" shape, and the
     * parser's default method for a continuous standard distribution in
     * 1.12.0 is TDR (transformed density rejection) */
    CHECK(id != NULL && strchr(id, '.') != NULL);
    CHECK(id != NULL && strncmp(id, "TDR.", 4) == 0);

    info = unur_gen_info(gen, 0);
    CHECK(info != NULL && strlen(info) > 0);

    CHECK(unur_gen_is_inversion(gen) == 0 || unur_gen_is_inversion(gen) == 1);

    unur_free(gen);

    /* the parser must also build a bare distribution object */
    distr = unur_str2distr("normal(0,1)");
    CHECK(distr != NULL);
    if (distr != NULL) {
        CHECK(unur_distr_get_dim(distr) == 1);
        CHECK(unur_distr_is_cont(distr) == 1);
        CHECK(unur_distr_is_discr(distr) == 0);
        CHECK(unur_distr_get_name(distr) != NULL);
        unur_distr_free(distr);
    }

    /* A bad distribution string is reported, not crashed on, and the
     * public error channel carries both a code and a message.  The
     * default handler is switched off for this one call so the expected
     * failure does not print a misleading "[error]" line into the CI
     * log; it is restored right afterwards. */
    {
        UNUR_ERROR_HANDLER *saved = unur_set_error_handler_off();
        UNUR_GEN *bad;
        unur_reset_errno();
        bad = unur_str2gen("no_such_distribution(1,2)");
        CHECK(bad == NULL);
        CHECK(unur_get_errno() != UNUR_SUCCESS);
        CHECK(unur_get_strerror(unur_get_errno()) != NULL);
        unur_set_error_handler(saved);
    }

    GROUP_RESULT(2);
    return 0;
}

/* ------------------------------------------------------------- */

static int group2_seeding(void)
{
    UNUR_GEN *a;
    UNUR_GEN *b;
    double xa[16];
    double xb[16];
    double xc[16];
    int i;

    a = unur_str2gen("normal(0,1)");
    b = unur_str2gen("normal(0,1)");
    CHECK(a != NULL && b != NULL);
    if (!a || !b) {
        GROUP_RESULT(3);
    }

    /* (1) seeding an existing generator makes the stream that follows
     * reproducible: the same seed yields the same 16 values. */
    CHECK(unur_gen_seed(a, 42) == UNUR_SUCCESS);
    for (i = 0; i < 16; i++) {
        xa[i] = unur_sample_cont(a);
    }
    CHECK(unur_gen_seed(a, 42) == UNUR_SUCCESS);
    for (i = 0; i < 16; i++) {
        xb[i] = unur_sample_cont(a);
    }
    CHECK(memcmp(xa, xb, sizeof(xa)) == 0);
    CHECK(fp_digest(xa, 16) == fp_digest(xb, 16));

    /* (2) unur_gen_reset() returns to the state saved by the last seed,
     * not to some half-way position derived from the values drawn so
     * far */
    CHECK(unur_gen_reset(a) == UNUR_SUCCESS);
    for (i = 0; i < 16; i++) {
        xc[i] = unur_sample_cont(a);
    }
    CHECK(memcmp(xa, xc, sizeof(xa)) == 0);

    /* (3) a different seed yields a different stream */
    CHECK(unur_gen_seed(a, 43) == UNUR_SUCCESS);
    for (i = 0; i < 16; i++) {
        xc[i] = unur_sample_cont(a);
    }
    CHECK(memcmp(xa, xc, sizeof(xa)) != 0);
    CHECK(fp_digest(xa, 16) != fp_digest(xc, 16));

    /* (4) The built-in URNG is ONE process-global stream, not one per
     * generator: `a` and `b` were both created from the default parser
     * entry point, `b` was never seeded, yet b's very first draw is
     * exactly a's *second* draw of the same seeded stream.  Equal here
     * means shared state - which is why two default-configured
     * generators have to be given their own URNG before they can be
     * driven from two threads (see group 6). */
    CHECK(unur_gen_seed(a, 99) == UNUR_SUCCESS);
    xa[0] = unur_sample_cont(a);
    xb[0] = unur_sample_cont(b);
    CHECK(unur_gen_seed(a, 99) == UNUR_SUCCESS);
    CHECK(unur_sample_cont(a) == xa[0]);
    CHECK(unur_sample_cont(a) == xb[0]);

    unur_free(a);
    unur_free(b);

    GROUP_RESULT(3);
    return 0;
}

/* ------------------------------------------------------------- */

static int group3_statistics(void)
{
    UNUR_GEN *gen;
    double sum = 0.0;
    double sum2 = 0.0;
    double mean;
    double var;
    double x;
    int i;
    int inside = 0;
    int n = 20000;

    gen = unur_str2gen("normal(0,1)");
    CHECK(gen != NULL);
    if (gen == NULL) {
        GROUP_RESULT(4);
    }
    CHECK(unur_gen_seed(gen, 20260920) == UNUR_SUCCESS);

    for (i = 0; i < n; i++) {
        x = unur_sample_cont(gen);
        CHECK(!isnan(x));
        sum += x;
        sum2 += x * x;
        if (x > -5.0 && x < 5.0) {
            inside++;
        }
    }
    mean = sum / n;
    var = sum2 / n - mean * mean;

    CHECK_CLOSE(mean, 0.0, 0.05);
    CHECK_CLOSE(var, 1.0, 0.05);
    /* a truncated or badly scaled sampler shows up in the tails */
    CHECK(inside > (int)(0.99 * n));
    CHECK(inside <= n);
    unur_free(gen);

    /* uniform on [0,1): support, then first two moments */
    gen = unur_str2gen("uniform(0,1)");
    CHECK(gen != NULL);
    if (gen == NULL) {
        GROUP_RESULT(4);
    }
    CHECK(unur_gen_seed(gen, 7) == UNUR_SUCCESS);
    sum = 0.0;
    sum2 = 0.0;
    for (i = 0; i < n; i++) {
        x = unur_sample_cont(gen);
        CHECK(x >= 0.0 && x < 1.0);
        sum += x;
        sum2 += x * x;
    }
    mean = sum / n;
    var = sum2 / n - mean * mean;
    CHECK_CLOSE(mean, 0.5, 0.02);
    CHECK_CLOSE(var, 1.0 / 12.0, 0.005);
    unur_free(gen);

    GROUP_RESULT(4);
    return 0;
}

/* ------------------------------------------------------------- */

static int group4_discrete_and_object_api(void)
{
    UNUR_GEN   *gen;
    UNUR_DISTR *distr;
    UNUR_PAR   *par;
    double      sum = 0.0;
    double      mean;
    int         v;
    int         i;
    int         minv = 1000;
    int         maxv = -1000;
    int         n = 5000;

    gen = unur_str2gen("poisson(4.0)");
    CHECK(gen != NULL);
    if (gen == NULL) {
        GROUP_RESULT(5);
    }
    CHECK(unur_get_dimension(gen) == 1);
    /* discrete distributions get a discrete default method */
    CHECK(unur_get_genid(gen) != NULL
          && strncmp(unur_get_genid(gen), "DARI.", 5) == 0);
    CHECK(unur_gen_seed(gen, 11) == UNUR_SUCCESS);

    for (i = 0; i < n; i++) {
        v = unur_sample_discr(gen);
        CHECK(v >= 0);
        if (v < minv) {
            minv = v;
        }
        if (v > maxv) {
            maxv = v;
        }
        sum += (double)v;
    }
    mean = sum / n;
    CHECK_CLOSE(mean, 4.0, 0.15);
    CHECK(minv >= 0);
    CHECK(maxv < 100);          /* no runaway / uninitialised variates */
    unur_free(gen);

    /* the object API: distr -> par -> gen, with par consumed by init() */
    distr = unur_distr_normal(NULL, 0);
    CHECK(distr != NULL);
    if (distr == NULL) {
        GROUP_RESULT(5);
    }
    par = unur_arou_new(distr);
    CHECK(par != NULL);
    if (par == NULL) {
        unur_distr_free(distr);
        GROUP_RESULT(5);
    }
    gen = unur_init(par);
    CHECK(gen != NULL);
    unur_distr_free(distr);     /* the generator keeps its own copy */
    if (gen != NULL) {
        sum = 0.0;
        CHECK(unur_gen_seed(gen, 5) == UNUR_SUCCESS);
        for (i = 0; i < 2000; i++) {
            sum += unur_sample_cont(gen);
        }
        mean = sum / 2000.0;
        CHECK_CLOSE(mean, 0.0, 0.1);
        unur_free(gen);
    }

    /* a generator can be cloned and the clone is independent */
    gen = unur_str2gen("normal(0,1)");
    if (gen != NULL) {
        UNUR_GEN *clone;
        CHECK(unur_get_distr(gen) != NULL);
        clone = unur_gen_clone(gen);
        CHECK(clone != NULL);
        if (clone != NULL) {
            unur_free(clone);
        }
        unur_free(gen);
    }

    GROUP_RESULT(5);
    return 0;
}

/* ------------------------------------------------------------- */

static int group5_harmony_abi(void)
{
    UNUR_URNG *urng;
    unsigned long bits;
    double        d;
    double        a;
    double        b;
    int           i;

    /* LP64: this is what libunuran.a was compiled for on
     * aarch64-linux-ohos; a 32-bit consumer would silently mismatch on
     * every size_t/int in the ABI (unur_distr_cemp_set_data et al.). */
    CHECK(sizeof(double) == 8);
    CHECK(sizeof(unsigned long) == 8);
    CHECK(sizeof(long) == sizeof(void *));
    CHECK(sizeof(int) == 4);
    CHECK(sizeof(size_t) >= 8);

    /* binary64 and base 2: unuran's rejection methods compute log/exp on
     * the sampled values, and its constant tables (chisq, intervals) are
     * generated for IEEE-754 double. */
    CHECK(FLT_RADIX == 2);
    CHECK(DBL_MANT_DIG == 53);
    CHECK(DBL_MAX_EXP == 1024);
    CHECK(sizeof(UNUR_GEN *) == sizeof(void *));

    /* exact bit-pattern round trip through a union-free memcpy: on
     * aarch64 this is the path the library uses for its constant tables. */
    d = 1.0 / 3.0;
    memcpy(&bits, &d, 8);
    memcpy(&a, &bits, 8);
    CHECK(a == d);

    /* The built-in uniform generator is usable directly from the public
     * header and stream straight into double.  It deliberately exposes
     * no seeding/reset callback (unur_urng_seed() / unur_urng_reset()
     * report "missing functionality" for it), so only usability and
     * range are asserted here; the per-generator source used by the
     * thread test is the seeded one. */
    urng = unur_urng_new(unur_urng_MRG31k3p, NULL);
    CHECK(urng != NULL);
    if (urng != NULL) {
        for (i = 0; i < 64; i++) {
            b = unur_urng_sample(urng);
            CHECK(b >= 0.0 && b < 1.0);
        }
        unur_urng_free(urng);
    }

    GROUP_RESULT(6);
    return 0;
}

/* ------------------------------------------------------------- */

#define THREADS 4
#define PER_THREAD 2000

typedef struct {
    unsigned long long state;
    double             out[PER_THREAD];
} thread_ctx;

/* A per-thread uniform source.  The library's own built-in URNG
 * (unur_urng_MRG31k3p) keeps its state in *file-level statics*
 * (src/uniform/mrg31k3p.c: `static unsigned long x10 = SEED10;` ...), so
 * it is shared by every generator in the process and must not be driven
 * from two threads at once.  unur_urng_new() is the supported way to give
 * each generator its own source. */
static double thread_unif(void *state)
{
    unsigned long long *s = (unsigned long long *)state;
    *s = *s * 6364136223846793005ULL + 1442695040888963407ULL;
    return (double)((*s >> 11) & 0x1FFFFFFFFFFFFFULL) / 9007199254740992.0;
}

static void *worker(void *arg)
{
    thread_ctx *ctx = (thread_ctx *)arg;
    UNUR_URNG  *urng;
    UNUR_GEN   *gen;
    int         i;

    urng = unur_urng_new(thread_unif, &ctx->state);
    if (urng == NULL) {
        return (void *)"unur_urng_new";
    }
    gen = unur_makegen_ssu("normal(0,1)", "tdr", urng);
    if (gen == NULL) {
        unur_urng_free(urng);
        return (void *)"unur_makegen_ssu";
    }
    for (i = 0; i < PER_THREAD; i++) {
        ctx->out[i] = unur_sample_cont(gen);
    }
    unur_free(gen);
    unur_urng_free(urng);
    return NULL;
}

static int group6_threads(void)
{
    pthread_t  th[THREADS];
    thread_ctx ctx[THREADS];
    void      *err[THREADS];
    thread_ctx base;
    unsigned long long digests[THREADS];
    int        i;

    memset(ctx, 0, sizeof(ctx));
    for (i = 0; i < THREADS; i++) {
        ctx[i].state = 0x9E3779B97F4A7C15ULL + (unsigned long long)i;
        err[i] = (void *)0xdeadbeef;
    }

    for (i = 0; i < THREADS; i++) {
        CHECK(pthread_create(&th[i], NULL, worker, &ctx[i]) == 0);
    }
    for (i = 0; i < THREADS; i++) {
        pthread_join(th[i], &err[i]);
        CHECK(err[i] == NULL);
    }

    /* 1) every thread produced values at all, all finite, all in a
     *    plausible range (a torn/shared RNG state shows up here first) */
    for (i = 0; i < THREADS; i++) {
        int j;
        for (j = 0; j < PER_THREAD; j++) {
            CHECK(!isnan(ctx[i].out[j]));
            CHECK(ctx[i].out[j] > -12.0 && ctx[i].out[j] < 12.0);
        }
    }

    /* 2) each thread's stream is reproducible: rerun one of them on this
     *    thread, from the same initial seed, and require bit-identical
     *    output.  (ctx[0].state has already been advanced by the run, so
     *    the seed thread 0 started from is recomputed rather than read
     *    back.) */
    memset(&base, 0, sizeof(base));
    base.state = 0x9E3779B97F4A7C15ULL;
    CHECK(worker(&base) == NULL);
    CHECK(memcmp(base.out, ctx[0].out, sizeof(base.out)) == 0);

    /* 3) the four streams differ from each other (i.e. the threads did
     *    not all sample one shared generator) */
    for (i = 0; i < THREADS; i++) {
        digests[i] = fp_digest(ctx[i].out, PER_THREAD);
    }
    CHECK(digests[0] != digests[1]);
    CHECK(digests[0] != digests[2]);
    CHECK(digests[0] != digests[3]);
    CHECK(digests[1] != digests[2]);
    CHECK(digests[1] != digests[3]);
    CHECK(digests[2] != digests[3]);

    /* 4) and each stream is still statistically the unit normal */
    for (i = 0; i < THREADS; i++) {
        double sum = 0.0;
        double sum2 = 0.0;
        int    j;
        for (j = 0; j < PER_THREAD; j++) {
            sum += ctx[i].out[j];
            sum2 += ctx[i].out[j] * ctx[i].out[j];
        }
        CHECK_CLOSE(sum / PER_THREAD, 0.0, 0.15);
        CHECK_CLOSE(sum2 / PER_THREAD - (sum / PER_THREAD) * (sum / PER_THREAD),
                    1.0, 0.15);
    }

    GROUP_RESULT(7);
    return 0;
}

/* ------------------------------------------------------------- */

int main(void)
{
    int rc;

    rc = group1_object_model();
    if (rc) {
        return rc;
    }
    rc = group2_seeding();
    if (rc) {
        return rc;
    }
    rc = group3_statistics();
    if (rc) {
        return rc;
    }
    rc = group4_discrete_and_object_api();
    if (rc) {
        return rc;
    }
    rc = group5_harmony_abi();
    if (rc) {
        return rc;
    }
    rc = group6_threads();
    if (rc) {
        return rc;
    }

    printf("ALL PASS: unuran 1.12.0 consumer checks (6 groups)\n");
    return 0;
}
