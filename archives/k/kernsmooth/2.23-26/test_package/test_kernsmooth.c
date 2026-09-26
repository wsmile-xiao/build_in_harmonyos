#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* kernsmooth.h declares the F77-mangled entry points (lowercase + underscore) */
#include <kernsmooth.h>

/* Real numerical verification of the KernSmooth Fortran core (R34):
 *   - linbin_: linear binning counts vs hand-computed values
 *   - rlbin_ : binned regression counts vs hand-computed values
 *   - locpol_: local polynomial regression (degree 1) recovers the identity
 *              line y = x within tolerance (orchestrated exactly as R's
 *              locpoly() does in R/all.R)
 */

static int failures = 0;

static void check_close(const char *name, double got, double want, double tol) {
    if (fabs(got - want) > tol) {
        printf("FAIL %s: got %.10f want %.10f\n", name, got, want);
        failures++;
    } else {
        printf("PASS %s: %.10f\n", name, got);
    }
}

int main(void) {
    /* ---- test 1: linbin_ (univariate linear binning) ---- */
    {
        double X[5] = {0.0, 0.25, 0.5, 1.0, 1.75};
        int n = 5, M = 5, trun = 0;
        double a = 0.0, b = 2.0;
        double gcnts[5];
        memset(gcnts, 0, sizeof(gcnts));
        linbin_(X, &n, &a, &b, &M, &trun, gcnts);
        printf("linbin gcnts: %f %f %f %f %f\n",
               gcnts[0], gcnts[1], gcnts[2], gcnts[3], gcnts[4]);
        /* delta = (2-0)/(5-1) = 0.5; hand-computed counts:
         * X=0.00 -> li=1 rem=0.00 -> g1+=1.0
         * X=0.25 -> li=1 rem=0.50 -> g1+=0.5 g2+=0.5
         * X=0.50 -> li=2 rem=0.00 -> g2+=1.0
         * X=1.00 -> li=3 rem=0.00 -> g3+=1.0
         * X=1.75 -> li=4 rem=0.50 -> g4+=0.5 g5+=0.5
         * g = {1.5, 1.5, 1.0, 0.5, 0.5}
         */
        check_close("linbin gcnts[0]", gcnts[0], 1.5, 1e-12);
        check_close("linbin gcnts[1]", gcnts[1], 1.5, 1e-12);
        check_close("linbin gcnts[2]", gcnts[2], 1.0, 1e-12);
        check_close("linbin gcnts[3]", gcnts[3], 0.5, 1e-12);
        check_close("linbin gcnts[4]", gcnts[4], 0.5, 1e-12);
    }

    /* ---- test 2: rlbin_ (regression-data linear binning) ---- */
    {
        double X[4] = {0.5, 1.0, 1.5, 2.0};
        double Y[4] = {1.0, 3.0, 2.0, 4.0};
        int n = 4, M = 4, trun = 0;
        double a = 0.0, b = 3.0;
        double xcnts[4], ycnts[4];
        rlbin_(X, Y, &n, &a, &b, &M, &trun, xcnts, ycnts);
        printf("rlbin xcnts: %f %f %f %f\n", xcnts[0], xcnts[1], xcnts[2], xcnts[3]);
        printf("rlbin ycnts: %f %f %f %f\n", ycnts[0], ycnts[1], ycnts[2], ycnts[3]);
        /* delta = 3/3 = 1.0; hand-computed:
         * X=0.5 -> li=1 rem=0.5 -> x1+=0.5 x2+=0.5 ; y1+=0.5*1 y2+=0.5*1
         * X=1.0 -> li=2 rem=0.0 -> x2+=1.0        ; y2+=3.0
         * X=1.5 -> li=2 rem=0.5 -> x2+=0.5 x3+=0.5; y2+=0.5*2 y3+=0.5*2
         * X=2.0 -> li=3 rem=0.0 -> x3+=1.0        ; y3+=4.0
         * x = {0.5, 2.0, 1.5, 0.0}  y = {0.5, 4.5, 5.0, 0.0}
         */
        check_close("rlbin xcnts[0]", xcnts[0], 0.5, 1e-12);
        check_close("rlbin xcnts[1]", xcnts[1], 2.0, 1e-12);
        check_close("rlbin xcnts[2]", xcnts[2], 1.5, 1e-12);
        check_close("rlbin ycnts[1]", ycnts[1], 4.5, 1e-12);
        check_close("rlbin ycnts[2]", ycnts[2], 5.0, 1e-12);
    }

    /* ---- test 3: locpol_ (local polynomial regression, degree 1) ---- */
    /* y = x exactly; local linear fit must reproduce the identity. */
    {
        const int n = 10, M = 10, Q = 1, pp = 2, ppp = 3;
        double X[10], Y[10];
        double a = 0.0, b = 0.9;
        const double h = 0.5;
        double xcnts[10], ycnts[10];
        int trun = 1, idrv = 0;
        double delta = (b - a) / (M - 1);
        double hdisc[1] = {h};
        int Lvec[1], indic[10], midpts[1], ipvt[2];
        double fkap[41], ss[10 * 3], tt[10 * 2];
        double Smat[2 * 2], Tvec[2], cvest[10];
        int i, k;

        for (i = 0; i < n; i++) { X[i] = i * 0.1; Y[i] = X[i]; }
        Lvec[0] = (int)floor(4 * h / delta);
        for (i = 0; i < M; i++) indic[i] = 1;
        memset(fkap, 0, sizeof(fkap));
        memset(midpts, 0, sizeof(midpts));
        memset(ss, 0, sizeof(ss));
        memset(tt, 0, sizeof(tt));
        memset(Smat, 0, sizeof(Smat));
        memset(Tvec, 0, sizeof(Tvec));
        memset(ipvt, 0, sizeof(ipvt));
        memset(cvest, 0, sizeof(cvest));

        rlbin_(X, Y, (int *)&n, &a, &b, (int *)&M, &trun, xcnts, ycnts);
        locpol_(xcnts, ycnts, &idrv, &delta, hdisc, Lvec, indic, midpts,
                (int *)&M, (int *)&Q, fkap, (int *)&pp, (int *)&ppp,
                ss, tt, Smat, Tvec, ipvt, cvest);

        printf("locpol cvest (identity y=x):");
        for (i = 0; i < M; i++) printf(" %.4f", cvest[i]);
        printf("\n");
        for (k = 2; k <= 7; k++) {
            double gx = a + k * delta;
            char label[64];
            snprintf(label, sizeof(label), "locpol fit[%d] vs x=%.1f", k, gx);
            check_close(label, cvest[k], gx, 1e-6);
        }
    }

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("%d TEST(S) FAILED\n", failures);
    return 1;
}
