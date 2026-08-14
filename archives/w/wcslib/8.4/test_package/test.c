#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/*
 * WCSLIB 8.4 test_package — calls the projection (prj) API.
 *
 * This test exercises the core WCSLIB library by:
 *   1. Initializing a TAN (tangent plane) projection via prjini()/prjset()
 *   2. Converting pixel coordinates to world coordinates via prjx2s()
 *   3. Converting world coordinates back to pixel coordinates via prjs2x()
 *   4. Verifying round-trip closure (forward then inverse should return
 *      approximately the original pixel coordinates)
 *
 * This is a substantive API test (R34) — it links against libwcs and
 * calls real WCSLIB functions, not just printing a string.
 */

#include <wcslib.h>
#include <prj.h>

int main(void)
{
    struct prjprm prj;
    int status;
    int stat[1];
    double x[1], y[1];
    double phi[1], theta[1];
    double xr[1], yr[1];
    double resid;

    /* Initialize the projection struct */
    prj.flag = 0;
    status = prjini(&prj);
    if (status != 0) {
        fprintf(stderr, "prjini failed with status %d\n", status);
        return 1;
    }

    /* Set up a TAN (gnomonic) projection */
    strcpy(prj.code, "TAN");
    /* Leave phi0, theta0 as UNDEFINED (set by prjini) to use defaults */

    status = prjset(&prj);
    if (status != 0) {
        fprintf(stderr, "prjset failed with status %d\n", status);
        prjfree(&prj);
        return 1;
    }

    /* Forward transform: pixel (x,y) -> intermediate world (phi,theta).
     * The last argument is an int stat[] array (one status value per
     * transformed element), NOT a wcsprm pointer. Passing NULL here
     * causes a NULL dereference inside tanx2s() (which does *statp = 0),
     * producing a SegFault. Always provide a valid stat buffer. */
    x[0] = 1.0;
    y[0] = 1.0;
    status = prjx2s(&prj, 1, 1, 1, 1, x, y, phi, theta, stat);
    if (status != 0) {
        fprintf(stderr, "prjx2s failed with status %d\n", status);
        prjfree(&prj);
        return 1;
    }
    if (stat[0] != 0) {
        fprintf(stderr, "prjx2s reported invalid (x,y), stat=%d\n", stat[0]);
        prjfree(&prj);
        return 1;
    }

    /* Inverse transform: intermediate world (phi,theta) -> pixel (x,y).
     * Same rationale for the stat[] argument. */
    status = prjs2x(&prj, 1, 1, 1, 1, phi, theta, xr, yr, stat);
    if (status != 0) {
        fprintf(stderr, "prjs2x failed with status %d\n", status);
        prjfree(&prj);
        return 1;
    }
    if (stat[0] != 0) {
        fprintf(stderr, "prjs2x reported invalid (phi,theta), stat=%d\n", stat[0]);
        prjfree(&prj);
        return 1;
    }

    /* Check round-trip closure */
    resid = fabs(x[0] - xr[0]) + fabs(y[0] - yr[0]);
    if (resid > 1.0e-10) {
        fprintf(stderr, "Round-trip closure failed: residual = %.1e\n", resid);
        prjfree(&prj);
        return 1;
    }

    printf("WCSLIB prj TAN projection test passed.\n");
    printf("  pixel (%.6f, %.6f) -> world (phi=%.6f, theta=%.6f) -> pixel (%.6f, %.6f)\n",
           x[0], y[0], phi[0], theta[0], xr[0], yr[0]);
    printf("  Round-trip residual: %.1e\n", resid);

    prjfree(&prj);
    return 0;
}
