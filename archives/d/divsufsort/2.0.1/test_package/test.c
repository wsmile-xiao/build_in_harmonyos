/*
 * test.c — Consumer test for divsufsort 2.0.1
 *
 * Verifies the core suffix array (divsufsort), suffix check (sufcheck),
 * Burrows-Wheeler Transform (divbwt), and inverse BWT (inverse_bw_transform)
 * APIs on a known input string.
 */
#include <divsufsort.h>
#include <divsufsort64.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(const char *msg) {
    fprintf(stderr, "FAIL: %s\n", msg);
    return 1;
}

int main(void) {
    /* Known input: "banana" — a classic suffix-array textbook example. */
    static const sauchar_t T[] = "banana";
    saidx_t n = (saidx_t)strlen((const char *)T);
    saidx_t *SA = (saidx_t *)malloc((size_t)n * sizeof(saidx_t));
    if (!SA) return fail("malloc SA failed");

    /* 1. Construct suffix array. */
    saint_t ret = divsufsort(T, SA, n);
    if (ret != 0) { free(SA); return fail("divsufsort returned non-zero"); }

    /* Expected suffix array for "banana" (0-indexed suffixes, SA[i] is
       the starting position of the i-th lexicographically smallest suffix):
         suffixes: a, ana, anana, banana, na, nana
         SA = [5, 3, 1, 0, 4, 2]  */
    static const saidx_t expected_SA[] = {5, 3, 1, 0, 4, 2};
    for (saidx_t i = 0; i < n; i++) {
        if (SA[i] != expected_SA[i]) {
            fprintf(stderr, "FAIL: SA[%d]=%d, expected %d\n", i, SA[i], expected_SA[i]);
            free(SA);
            return 1;
        }
    }

    /* 2. Verify the suffix array with upstream sufsufcheck. */
    saint_t chk = sufcheck(T, SA, n, 0);
    if (chk != 0) { free(SA); return fail("sufcheck reported invalid suffix array"); }

    /* 3. Burrows-Wheeler Transform.
       divbwt() prepends T[n-1] at U[0] and returns pidx (primary index).
       For "banana" the BWT output is "annbaa". Rather than hardcode pidx
       (which depends on internal SA-IS bucket ordering), we verify the
       full round-trip: inverse_bw_transform must recover the original
       string from (U, pidx).  */
    sauchar_t *U = (sauchar_t *)malloc((size_t)n * sizeof(sauchar_t));
    saidx_t *A = (saidx_t *)malloc((size_t)n * sizeof(saidx_t));
    if (!U || !A) { free(SA); free(U); free(A); return fail("malloc BWT failed"); }

    saidx_t pidx = divbwt(T, U, A, n);
    if (pidx < 0) { free(SA); free(U); free(A); return fail("divbwt failed"); }

    /* Verify BWT string: divsufsort convention prepends T[n-1]='a' at U[0]. */
    static const sauchar_t expected_BWT[] = "annbaa";
    if (memcmp(U, expected_BWT, (size_t)n) != 0) {
        fprintf(stderr, "FAIL: BWT mismatch: got \"");
        for (saidx_t i = 0; i < n; i++) fputc(U[i], stderr);
        fprintf(stderr, "\", expected \"annbaa\"\n");
        free(SA); free(U); free(A);
        return 1;
    }

    /* 4. Inverse BWT — should recover the original string. */
    sauchar_t *R = (sauchar_t *)malloc((size_t)n * sizeof(sauchar_t));
    if (!R) { free(SA); free(U); free(A); free(R); return fail("malloc inverse failed"); }

    /* inverse_bw_transform returns saint_t status:
     * 0 on success, -1/-2 on error.
     */
    if (inverse_bw_transform(U, R, A, n, pidx) < 0) {
        free(SA);
        free(U);
        free(A);
        free(R);
        return fail("inverse_bw_transform failed");
    }
    if (memcmp(R, T, (size_t)n) != 0) {
        fprintf(stderr, "FAIL: inverse BWT did not recover original string\n");
        free(SA); free(U); free(A); free(R);
        return 1;
    }

    /* 5. Version string sanity check. */
    const char *ver = divsufsort_version();
    if (!ver || ver[0] == '\0') {
        free(SA); free(U); free(A); free(R);
        return fail("divsufsort_version returned empty");
    }

    free(SA);
    free(U);
    free(A);
    free(R);


    /* 64-bit component verification: divsufsort64 */
    {
        saidx64_t SA64[6];
        static const saidx64_t expected_SA64[6] = {5, 3, 1, 0, 4, 2};

        if (divsufsort64(T, SA64, (saidx64_t)n) != 0) {
            return fail("divsufsort64 failed");
        }

        for (saidx_t i = 0; i < n; ++i) {
            if (SA64[i] != expected_SA64[i]) {
                return fail("divsufsort64 suffix array mismatch");
            }
        }

        if (sufcheck64(T, SA64, (saidx64_t)n, 0) != 0) {
            return fail("sufcheck64 failed");
        }
    }

    printf("PASS: divsufsort, sufcheck, divbwt, inverse_bw_transform, divsufsort64, sufcheck64, version=%s\n", ver);
    return 0;
}
