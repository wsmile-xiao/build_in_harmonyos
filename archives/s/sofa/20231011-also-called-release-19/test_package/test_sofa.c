#include <math.h>
#include <stdio.h>

#include <sofa.h>

static double dabs(double x) {
    return x < 0.0 ? -x : x;
}

int main(void) {
    int failures = 0;

    /* TC1: calendar <-> Julian date roundtrip for the release date itself.
       MJD zero point 2400000.5 is an API contract; the roundtrip proves the
       date conversion links and computes correctly. */
    {
        double djm0 = 0.0, djm1 = 0.0;
        int iy = 0, im = 0, id = 0;
        double fd = 0.0;
        int j = iauCal2jd(2023, 10, 11, &djm0, &djm1);
        int k = iauJd2cal(djm0, djm1, &iy, &im, &id, &fd);
        if (j != 0 || k != 0 || djm0 != 2400000.5 || iy != 2023 || im != 10 || id != 11) {
            printf("TC1 iauCal2jd/iauJd2cal FAILED: j=%d k=%d djm0=%.1f date=%d-%d-%d\n",
                   j, k, djm0, iy, im, id);
            failures++;
        } else {
            printf("TC1 iauCal2jd/iauJd2cal OK: djm0=%.1f djm1=%.6f -> %d-%02d-%02d\n",
                   djm0, djm1, iy, im, id);
        }
    }

    /* TC2: Besselian epoch roundtrip through MJD. */
    {
        double djm0 = 0.0, djm1 = 0.0;
        iauEpb2jd(1982.418, &djm0, &djm1);
        double epb = iauEpb(djm0, djm1);
        if (dabs(epb - 1982.418) > 1e-9) {
            printf("TC2 iauEpb2jd/iauEpb FAILED: epb=%.12f\n", epb);
            failures++;
        } else {
            printf("TC2 iauEpb2jd/iauEpb OK: epb=%.12f\n", epb);
        }
    }

    /* TC3: TAI-UTC for 2023-10-11. No leap second has been introduced since
       2016, so TAI-UTC stays inside [30, 40] s; the status must be 0. */
    {
        double dat = 0.0;
        int s = iauDat(2023, 10, 11, 0.0, &dat);
        if (s != 0 || dat < 30.0 || dat > 40.0) {
            printf("TC3 iauDat FAILED: status=%d dat=%.6f\n", s, dat);
            failures++;
        } else {
            printf("TC3 iauDat OK: TAI-UTC=%.1f s\n", dat);
        }
    }

    /* TC4: Earth rotation angle at J2000 must fall in [0, 2pi). */
    {
        double era = iauEra00(2451545.0, 0.0);
        if (!(era >= 0.0 && era < 6.283185307179586)) {
            printf("TC4 iauEra00 FAILED: era=%.12f\n", era);
            failures++;
        } else {
            printf("TC4 iauEra00 OK: era=%.12f rad\n", era);
        }
    }

    /* Silence -Wunused warnings for the math header on strict toolchains. */
    (void)fabs(0.0);

    if (failures != 0) {
        printf("SOFA consumer test: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("SOFA consumer test: all 4 checks passed\n");
    return 0;
}
