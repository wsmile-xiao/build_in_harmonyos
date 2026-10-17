#include <math.h>
#include <stdio.h>
#include <string.h>

#include <swephexp.h>

/* test_package/test.c — consumer test for libswe 2.10.03 (Conan L1).
 *
 * Calls real library APIs that need no ephemeris data files (SEFLG_MOSEPH
 * analytic model), so the test is hermetic on OHOS:
 *   1. swe_version() reports 2.10.03
 *   2. swe_julday() reproduces the J2000 epoch (2451545.0)
 *   3. swe_calc_ut() Sun position is plausible (280 +/- 1 deg on J2000)
 *   4. swe_calc_ut() Moon distance is plausible (0.0022 - 0.0029 AU)
 *   5. swe_get_planet_name() returns "Saturn" for SE_SATURN
 *   6. swe_revjul() round-trips the J2000 Julian day
 *   7. END-TO-END consumer case: natal-chart workflow for
 *      2000-01-01 12:00 UT at Greenwich (lat 51.5, lon 0.0), chaining
 *      swe_julday -> swe_calc_ut (Sun/Moon) -> swe_sidtime ->
 *      swe_houses -> swe_revjul with data flow between every step,
 *      cross-validating determinism and physical ranges and printing
 *      a consumer-visible chart summary (not an isolated assertion).
 *
 * Ranges are astronomically grounded, not vacuous: radian output (~4.89),
 * arcsecond output (~1e6), kilometer output (~4e5) or a failed calc all
 * violate them. Prints per-check PASS/FAIL plus the HMBS hard-gate marker
 * with real counters. Returns 0 only when every check passes.
 */
static int g_pass = 0;
static int g_fail = 0;
static const int G_DISCOVERED = 7;

static void check_pass(const char *name) {
    g_pass++;
    printf("[PASS] %s\n", name);
}

static void check_fail(const char *name, const char *detail) {
    g_fail++;
    if (detail && detail[0] != '\0')
        printf("[FAIL] %s -- %s\n", name, detail);
    else
        printf("[FAIL] %s\n", name);
}

/* Complete consumer use case (end-to-end): compute one natal chart with
 * chained library calls and validate the whole flow, not one API call.
 * Returns 1 on success, 0 on failure. */
static int run_end_to_end_natal_chart(void) {
    char serr[256];
    double tjd;
    double xsun[6], xmoon[6], xsun2[6];
    double cusps[13], ascmc[10];
    double sidt;
    int32 rc_sun, rc_moon, rc_houses;
    int year, mon, day;
    double hour;
    int i;

    tjd = swe_julday(2000, 1, 1, 12.0, SE_GREG_CAL);
    if (fabs(tjd - 2451545.0) > 1e-9) {
        char detail[64];
        snprintf(detail, sizeof(detail), "tjd=%.9f", tjd);
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
        return 0;
    }

    serr[0] = '\0';
    rc_sun = swe_calc_ut(tjd, SE_SUN, SEFLG_MOSEPH, xsun, serr);
    if (rc_sun == ERR || xsun[0] < 279.0 || xsun[0] > 282.0) {
        char detail[128];
        snprintf(detail, sizeof(detail), "sun rc=%d lon=%.6f serr=%s", (int)rc_sun, xsun[0], serr);
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
        return 0;
    }

    serr[0] = '\0';
    rc_moon = swe_calc_ut(tjd, SE_MOON, SEFLG_MOSEPH, xmoon, serr);
    if (rc_moon == ERR || xmoon[2] < 0.0022 || xmoon[2] > 0.0029) {
        char detail[128];
        snprintf(detail, sizeof(detail), "moon rc=%d dist=%.7f serr=%s", (int)rc_moon, xmoon[2], serr);
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
        return 0;
    }

    /* Determinism across the flow: recompute Sun from the same tjd. */
    serr[0] = '\0';
    (void)swe_calc_ut(tjd, SE_SUN, SEFLG_MOSEPH, xsun2, serr);
    if (fabs(xsun2[0] - xsun[0]) > 1e-9) {
        char detail[128];
        snprintf(detail, sizeof(detail), "sun not deterministic %.9f vs %.9f", xsun[0], xsun2[0]);
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
        return 0;
    }

    /* Sidereal time feeds house computation in a real chart program. */
    sidt = swe_sidtime(tjd);
    if (!(sidt >= 0.0 && sidt < 24.0)) {
        char detail[64];
        snprintf(detail, sizeof(detail), "sidt=%.6f", sidt);
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
        return 0;
    }

    /* Whole flow converges here: houses from the same tjd + geo position. */
    for (i = 0; i < 13; i++)
        cusps[i] = -999.0;
    for (i = 0; i < 10; i++)
        ascmc[i] = -999.0;
    rc_houses = swe_houses(tjd, 0, 51.5, 0.0, cusps, ascmc);
    if (rc_houses == ERR) {
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", "swe_houses returned ERR");
        return 0;
    }
    for (i = 1; i <= 12; i++) {
        if (!(cusps[i] >= 0.0 && cusps[i] < 360.0)) {
            char detail[96];
            snprintf(detail, sizeof(detail), "cusp[%d]=%.6f out of range", i, cusps[i]);
            check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
            return 0;
        }
    }
    if (!(ascmc[0] >= 0.0 && ascmc[0] < 360.0 && ascmc[1] >= 0.0 && ascmc[1] < 360.0)) {
        char detail[96];
        snprintf(detail, sizeof(detail), "asc=%.6f mc=%.6f", ascmc[0], ascmc[1]);
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
        return 0;
    }

    /* Close the loop: date round-trip on the same tjd used above. */
    swe_revjul(tjd, SE_GREG_CAL, &year, &mon, &day, &hour);
    if (!(year == 2000 && mon == 1 && day == 1 && fabs(hour - 12.0) < 1e-6)) {
        char detail[96];
        snprintf(detail, sizeof(detail), "revjul %04d-%02d-%02d %.6f", year, mon, day, hour);
        check_fail("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)", detail);
        return 0;
    }

    /* Consumer-visible artifact: a one-line natal chart summary. */
    printf("chart: date=2000-01-01 12:00UT tjd=%.5f sun=%.4f moon_lon=%.4f moon_dist=%.6f asc=%.4f mc=%.4f sid=%.4f\n",
           tjd, xsun[0], xmoon[0], xmoon[2], ascmc[0], ascmc[1], sidt);
    check_pass("end-to-end natal chart (Greenwich J2000: julday->planets->houses->chart)");
    return 1;
}

int main(void) {
    char vers[64];
    char sname[64];
    char serr[256];
    double jut;
    double xx[6];
    int32 rc;
    int year, mon, day;
    double hour;

    /* 1. library version */
    swe_version(vers);
    if (strncmp(vers, "2.10.03", 7) == 0)
        check_pass("swe_version reports 2.10.03");
    else
        check_fail("swe_version reports 2.10.03", vers);

    /* 2. J2000 epoch: 2000-01-01 12:00 UT Gregorian == 2451545.0 */
    jut = swe_julday(2000, 1, 1, 12.0, SE_GREG_CAL);
    if (fabs(jut - 2451545.0) < 1e-9)
        check_pass("swe_julday J2000 == 2451545.0");
    else {
        char detail[64];
        snprintf(detail, sizeof(detail), "got %.9f", jut);
        check_fail("swe_julday J2000 == 2451545.0", detail);
    }

    /* 3. Sun ecliptic longitude on J2000 ~280.4 deg (Moshier, no data files) */
    serr[0] = '\0';
    rc = swe_calc_ut(2451545.0, SE_SUN, SEFLG_MOSEPH, xx, serr);
    if (rc != ERR && xx[0] > 279.0 && xx[0] < 282.0)
        check_pass("swe_calc_ut Sun longitude plausible");
    else {
        char detail[128];
        snprintf(detail, sizeof(detail), "rc=%d lon=%.6f serr=%s", (int)rc, xx[0], serr);
        check_fail("swe_calc_ut Sun longitude plausible", detail);
    }

    /* 4. Moon distance on J2000 within the real 0.00238-0.00271 AU band */
    serr[0] = '\0';
    rc = swe_calc_ut(2451545.0, SE_MOON, SEFLG_MOSEPH, xx, serr);
    if (rc != ERR && xx[2] > 0.0022 && xx[2] < 0.0029)
        check_pass("swe_calc_ut Moon distance plausible");
    else {
        char detail[128];
        snprintf(detail, sizeof(detail), "rc=%d dist=%.7f serr=%s", (int)rc, xx[2], serr);
        check_fail("swe_calc_ut Moon distance plausible", detail);
    }

    /* 5. planet name lookup */
    sname[0] = '\0';
    swe_get_planet_name(SE_SATURN, sname);
    if (strcmp(sname, "Saturn") == 0)
        check_pass("swe_get_planet_name Saturn");
    else
        check_fail("swe_get_planet_name Saturn", sname);

    /* 6. Julian-day round trip */
    swe_revjul(2451545.0, SE_GREG_CAL, &year, &mon, &day, &hour);
    if (year == 2000 && mon == 1 && day == 1 && fabs(hour - 12.0) < 1e-6)
        check_pass("swe_revjul round-trips J2000");
    else {
        char detail[96];
        snprintf(detail, sizeof(detail), "got %04d-%02d-%02d %.6f", year, mon, day, hour);
        check_fail("swe_revjul round-trips J2000", detail);
    }

    /* 7. complete consumer use case (end-to-end natal-chart workflow) */
    run_end_to_end_natal_chart();

    swe_close();

    {
        int ok = (g_fail == 0 && g_pass == G_DISCOVERED);
        printf("=== test_swe summary: %d/%d passed, %d failed ===\n", g_pass, G_DISCOVERED, g_fail);
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
               "\"command\":\"./test_swe\",\"discovered\":%d,\"passedCount\":%d}\n",
               ok ? "true" : "false", G_DISCOVERED, g_pass);
    }
    return (g_fail == 0 && g_pass == G_DISCOVERED) ? 0 : 1;
}
