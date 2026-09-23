/*------------------------------------------------------------------------------
* Consumer test for the rtklib Conan package
*
* Compiled against the *installed* include/rtklib.h and linked with the
* *installed* lib/libRTK.a.  Every check below is an exact numeric assertion
* whose expected value follows from the RTKLIB implementation itself (calendar
* and GPS-time round trips, ECEF/geodetic round trip, closed-form geometric
* range, a 2x2 inverse, vector identities), so a missing, stale, truncated or
* wrong-architecture archive fails here even though it would still compile.
*
* No assert() is used: the test must behave identically with and without
* NDEBUG, which Conan defines for Release builds.
*-----------------------------------------------------------------------------*/
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include "rtklib.h"

static int n_checks = 0;
static int n_fail = 0;

static void check(int ok, const char *what)
{
    n_checks++;
    if (ok) {
        printf("  ok   : %s\n", what);
    }
    else {
        n_fail++;
        printf("  FAIL : %s\n", what);
    }
}

static int near(double a, double b, double tol)
{
    return fabs(a - b) <= tol;
}

int main(void)
{
    double ep[6] = {2005, 4, 2, 0, 0, 0.0}, ep2[6];
    double pos[3], r2[3], rs[3], rr[3], e[3], azel[2], d, tow;
    double *A, *Ai, *P, *I;
    double v1[3] = {1.0, 2.0, 3.0}, v2[3] = {4.0, 5.0, 6.0}, v3[3];
    gtime_t t, t2;
    int week = 0, prn = 0, i, j, ok;

    printf("rtklib consumer test (installed rtklib.h + libRTK.a)\n");

    /* ── 1. time: calendar <-> gtime_t <-> GPS week / second of week ───── */
    t = epoch2time(ep);
    time2epoch(t, ep2);
    ok = 1;
    for (i = 0; i < 6; i++) {
        if (!near(ep[i], ep2[i], 1e-6)) ok = 0;
    }
    check(ok, "epoch2time/time2epoch round trip for 2005-04-02 00:00:00");

    tow = time2gpst(t, &week);
    check(week == 1316, "time2gpst() week == 1316");
    check(near(tow, 518400.0, 1e-6), "time2gpst() second of week == 518400");
    t2 = gpst2time(week, tow);
    check(near(timediff(t2, t), 0.0, 1e-6), "gpst2time/time2gpst round trip");

    /* ── 2. coordinates: ECEF <-> geodetic on the ellipsoid equator ────── */
    rr[0] = RE_WGS84; rr[1] = 0.0; rr[2] = 0.0;         /* lat=0 lon=0 h=0 */
    ecef2pos(rr, pos);
    check(near(pos[0], 0.0, 1e-12) && near(pos[1], 0.0, 1e-12) && near(pos[2], 0.0, 1e-6),
          "ecef2pos(RE_WGS84,0,0) == (0,0,0)");
    pos2ecef(pos, r2);
    check(near(r2[0], RE_WGS84, 1e-6) && near(r2[1], 0.0, 1e-6) && near(r2[2], 0.0, 1e-6),
          "pos2ecef/ecef2pos round trip");

    /* ── 3. geometric range: no Sagnac term for an x-axis offset ───────── */
    rs[0] = RE_WGS84 + 20200000.0; rs[1] = 0.0; rs[2] = 0.0;
    d = geodist(rs, rr, e);
    check(near(d, 20200000.0, 1e-6), "geodist() == 20200000 m");
    check(near(e[0], 1.0, 1e-12) && near(e[1], 0.0, 1e-12) && near(e[2], 0.0, 1e-12),
          "geodist() returns the unit line-of-sight vector");

    /* a satellite straight up from (0,0) is at 90 deg elevation, 0 deg azimuth */
    pos[0] = 0.0; pos[1] = 0.0; pos[2] = 0.0;
    check(near(satazel(pos, e, azel), PI / 2.0, 1e-12), "satazel() returns 90 deg elevation");
    check(near(azel[0], 0.0, 1e-12) && near(azel[1], PI / 2.0, 1e-12),
          "satazel() azel == (0, 90 deg)");

    /* ── 4. vector and matrix routines ─────────────────────────────────── */
    check(near(dot(v1, v2, 3), 32.0, 1e-12), "dot([1,2,3],[4,5,6]) == 32");
    check(near(norm(v1, 3), sqrt(14.0), 1e-12), "norm([1,2,3]) == sqrt(14)");
    cross3(v1, v2, v3);
    check(near(v3[0], -3.0, 1e-12) && near(v3[1], 6.0, 1e-12) && near(v3[2], -3.0, 1e-12),
          "cross3([1,2,3],[4,5,6]) == [-3,6,-3]");

    A = mat(2, 2); Ai = mat(2, 2); P = mat(2, 2); I = eye(2);
    /* column major storage of the row-major matrix [[4,7],[2,6]], det = 10 */
    A[0] = 4.0; A[1] = 2.0; A[2] = 7.0; A[3] = 6.0;
    matcpy(Ai, A, 2, 2);
    check(matinv(Ai, 2) == 0, "matinv([[4,7],[2,6]]) returns 0");
    check(near(Ai[0], 0.6, 1e-12) && near(Ai[1], -0.2, 1e-12) &&
          near(Ai[2], -0.7, 1e-12) && near(Ai[3], 0.4, 1e-12),
          "matinv() == [[0.6,-0.7],[-0.2,0.4]]");
    matmul("NN", 2, 2, 2, 1.0, A, Ai, 0.0, P);
    ok = 1;
    for (i = 0; i < 2; i++) {
        for (j = 0; j < 2; j++) {
            if (!near(P[i + j * 2], I[i + j * 2], 1e-12)) ok = 0;
        }
    }
    check(ok, "A * inv(A) == I through matmul()");

    /* ── 5. satellite numbering ────────────────────────────────────────── */
    check(satno(SYS_GPS, 5) == 5, "satno(SYS_GPS,5) == 5");
    check(satsys(5, &prn) == SYS_GPS && prn == 5, "satsys(5) == SYS_GPS / prn 5");
    check(satsys(satno(SYS_GAL, 3), &prn) == SYS_GAL && prn == 3,
          "satno/satsys round trip for Galileo prn 3");

    free(A); free(Ai); free(P); free(I);

    printf("%s: %d checks, %d failed\n", n_fail ? "FAILED" : "PASSED", n_checks, n_fail);
    return n_fail ? 1 : 0;
}
