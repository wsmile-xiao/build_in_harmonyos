/* Consumer test for the installed oourafft static libraries.
 *
 * Upstream ships no public headers (only alloc.h); the FFT prototypes are the
 * documented calling convention from the source block comments, so we declare
 * them here exactly as the upstream test program does.  The test exercises
 * fft2d_fftsg (1-D cdft/rdft), fft2d_fftsg2d (2-D cdft2d) and fft2d_alloc. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "alloc.h"

void cdft(int n, int isgn, double *a, int *ip, double *w);
void rdft(int n, int isgn, double *a, int *ip, double *w);
void cdft2d(int n1, int n2, int isgn, double **a, double *t, int *ip, double *w);

static int checks = 0;
static int fails = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (!(cond)) { fails++; printf("FAIL: %s\n", (msg)); } \
} while (0)

#define RND(p) ((*(p) = (*(p) * 7141 + 54773) % 259200) * (1.0 / 259200.0))

static void putdata(int nini, int nend, double *a)
{
    int j, seed = 0;
    for (j = nini; j <= nend; j++)
        a[j] = RND(&seed);
}

static double errorcheck(int nini, int nend, double scale, double *a)
{
    int j, seed = 0;
    double err = 0, e;
    for (j = nini; j <= nend; j++) {
        e = fabs(RND(&seed) - a[j] * scale);
        if (e > err)
            err = e;
    }
    return err;
}

int main(void)
{
    const int n = 64;
    int ip[64 + 2];
    double a[64];
    double w[64 * 5 / 4];
    int j;

    CHECK(fabs(cos(0.0) - 1.0) < 1e-12, "libm visible");

    /* cdft forward+inverse round trip */
    ip[0] = 0;
    putdata(0, n - 1, a);
    cdft(n, 1, a, ip, w);
    cdft(n, -1, a, ip, w);
    CHECK(errorcheck(0, n - 1, 2.0 / n, a) < 1e-9, "cdft round trip");

    /* rdft forward+inverse round trip */
    ip[0] = 0;
    putdata(0, n - 1, a);
    rdft(n, 1, a, ip, w);
    rdft(n, -1, a, ip, w);
    CHECK(errorcheck(0, n - 1, 2.0 / n, a) < 1e-9, "rdft round trip");

    /* alloc helpers */
    {
        double *d = alloc_1d_double(16);
        CHECK(d != NULL, "alloc_1d_double");
        if (d) {
            for (j = 0; j < 16; j++)
                d[j] = j;
            CHECK(d[15] == 15.0, "alloc_1d_double contents");
            free_1d_double(d);
        }
    }

    /* 2-D complex DFT round trip (fftsg2d + fftsg) */
    {
        const int n1 = 4, n2 = 4;      /* logical 4x4, stored a[4][8] */
        double **m = alloc_2d_double(n1, 2 * n2);
        double **orig = alloc_2d_double(n1, 2 * n2);
        double t[8 * n1];
        int ip2[64 + 2];
        double w2[64];
        int bad = 0, j1, j2, seed = 42;
        CHECK(m != NULL && orig != NULL, "alloc_2d_double");
        if (m && orig) {
            for (j1 = 0; j1 < n1; j1++)
                for (j2 = 0; j2 < 2 * n2; j2++) {
                    m[j1][j2] = RND(&seed);
                    orig[j1][j2] = m[j1][j2];
                }
            ip2[0] = 0;
            cdft2d(n1, 2 * n2, 1, m, t, ip2, w2);
            cdft2d(n1, 2 * n2, -1, m, t, ip2, w2);
            for (j1 = 0; j1 < n1; j1++)
                for (j2 = 0; j2 < 2 * n2; j2++) {
                    m[j1][j2] /= (double)(n1 * n2);
                    if (fabs(m[j1][j2] - orig[j1][j2]) > 1e-9)
                        bad = 1;
                }
            CHECK(!bad, "cdft2d round trip");
            free_2d_double(m);
            free_2d_double(orig);
        }
    }

    printf("OOURAFFT_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
