/* OHOS-specific runtime check for the packaged libnova library.
 *
 * Compiled and linked against the FINAL conan package (public headers +
 * library) and executed on the OpenHarmony PC as checkpoint C11 of
 * test_ohos.sh. It runs a real astronomy flow with textbook-anchored
 * tolerances (no tautological, non-zero-only or over-loose assertions):
 *
 *   1. Julian day anchor: 2000-01-01 12:00:00 UT == JD 2451545.0 exactly
 *      (tolerance 1e-9 day, i.e. double round-trip noise only).
 *   2. Mean obliquity of the ecliptic at J2000.0 (IAU 1980 theory,
 *      Meeus 22.2): eps0 = 23 deg 26' 21.448" = 23.43929111 deg
 *      (tolerance 1e-6 deg; libnova's nutation.c implements the same
 *      IAU polynomial, whose T=0 constant is printed to 8 decimals).
 *   3. Greenwich mean sidereal time at the J2000.0 epoch itself:
 *      GMST(D=0) = 18h 41m 50.548s = 18.697374558 h - the constant term
 *      of the IAU 1982 polynomial libnova's sidereal.c implements,
 *      280.46061837 deg / 15 (tolerance 1e-6 h = 3.6 ms of time).
 */
#include <math.h>
#include <stdio.h>

#include <libnova/libnova.h>

static int failures;

static void check_eps(const char *name, double got, double want, double tol)
{
    double delta = fabs(got - want);
    printf("%s: %.10f (want %.10f +/- %.1e)\n", name, got, want, tol);
    if (!(delta <= tol)) {
        printf("  -> FAIL (delta %.3e)\n", delta);
        failures++;
    }
}

int main(void)
{
    /* JD of the J2000.0 epoch: 2000-01-01 12:00 UT. */
    struct ln_date j2000 = {2000, 1, 1, 12, 0, 0.0};
    double jd = ln_get_julian_day(&j2000);
    check_eps("JD 2000-01-01 12:00 UT", jd, 2451545.0, 1e-9);

    /* Mean obliquity at J2000.0 (ln_nutation.ecliptic field). */
    struct ln_nutation nut;
    ln_get_nutation(jd, &nut);
    check_eps("mean obliquity J2000.0 (deg)", nut.ecliptic, 23.43929111,
              1e-6);

    /* GMST at the J2000.0 epoch itself (hours). */
    check_eps("GMST J2000.0 (h)", ln_get_mean_sidereal_time(jd),
              18.697374558, 1e-6);

    if (failures) {
        printf("ohos_check: %d FAILURE(S)\n", failures);
        return 1;
    }
    printf("OHOS_ASTRONOMY_OK\n");
    return 0;
}
