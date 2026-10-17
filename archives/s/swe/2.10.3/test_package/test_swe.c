/* Consumer test for swe 2.10.3 (Swiss Ephemeris) on HarmonyOS PC.
 *
 * Real API coverage (Moshier mode, no ephemeris files needed):
 *  1. swe_julday(2000,1,1,12.0 Gregorian) must equal 2451545.0 exactly.
 *  2. swe_version() must report 2.10.3.
 *  3. swe_calc_ut() Sun/Moshier on J2000 must return rc >= 0 with longitude
 *     in [279, 282] degrees.
 *  4. swe_get_planet_name(SE_SUN) must return "Sun".
 *  5. swe_sidtime() must be finite and in [0, 24).
 *  6. swe_houses_ex() Moshier/Placidus must return OK.
 *  7. Ascendant ascmc[0] must be in [0, 360).
 *  8. swe_get_ayanamsa_ex_ut() Lahiri/Moshier must return OK.
 *  9. Lahiri ayanamsa for 2007 must be in (20, 25) degrees.
 * 10. swe_calc_ut() Moon/Moshier must return rc >= 0 with longitude
 *     in [0, 360).
 * Emits HMBS_TEST_PACKAGE_RESULT with the real counters after asserting.
 */
#include <stdio.h>
#include <string.h>
#include <swephexp.h>

int main(void) {
    const int discovered = 10;
    int passed = 0;
    char serr[256];
    double tjd;

    swe_set_ephe_path(NULL);

    /* Case 1: Julian day of J2000.0 (2000-01-01 12:00 UT, Gregorian). */
    {
        double jd = swe_julday(2000, 1, 1, 12.0, SE_GREG_CAL);
        printf("swe_julday(2000,1,1,12.0) = %.6f\n", jd);
        if (jd == 2451545.0) {
            ++passed;
        } else {
            printf("FAIL: expected 2451545.0\n");
        }
    }

    /* Case 2: library version string. */
    {
        char ver[256];
        ver[0] = '\0';
        swe_version(ver);
        printf("swe_version = %s\n", ver);
        /* Upstream SE_VERSION is "2.10.03" (tag v2.10.3final); accept both. */
        if (strncmp(ver, "2.10.", 5) == 0) {
            ++passed;
        } else {
            printf("FAIL: expected version prefix 2.10.\n");
        }
    }

    /* Case 3: Sun position, Moshier analytical ephemeris (offline-safe). */
    {
        double xx[6] = {0};
        serr[0] = '\0';
        {
            int32 rc = swe_calc_ut(2451545.0, SE_SUN, SEFLG_MOSEPH | SEFLG_SPEED, xx, serr);
            printf("swe_calc_ut Sun rc=%d lon=%.6f lat=%.6f serr=%s\n",
                   (int) rc, xx[0], xx[1], serr);
            if (rc >= 0 && xx[0] > 279.0 && xx[0] < 282.0) {
                ++passed;
            } else {
                printf("FAIL: Sun longitude out of [279,282]\n");
            }
        }
    }

    /* Case 4: planet name lookup. */
    {
        char name[256];
        name[0] = '\0';
        swe_get_planet_name(SE_SUN, name);
        printf("swe_get_planet_name(0) = %s\n", name);
        if (strcmp(name, "Sun") == 0) {
            ++passed;
        } else {
            printf("FAIL: expected Sun\n");
        }
    }

    tjd = swe_julday(2007, 3, 3, 0.0, SE_GREG_CAL);

    /* Case 5: sidereal time is finite and in [0, 24). */
    {
        double sidt = swe_sidtime(tjd);
        printf("swe_sidtime = %.6f\n", sidt);
        if (sidt == sidt && sidt >= 0.0 && sidt < 24.0) {
            ++passed;
        } else {
            printf("FAIL: sidereal time out of range\n");
        }
    }

    /* Cases 6-7: Placidus houses (Moshier) for New York. */
    {
        double cusps[13] = {0};
        double ascmc[10] = {0};
        int rc = swe_houses_ex(tjd, SEFLG_MOSEPH, 40.7128, -74.0060, 'P', cusps, ascmc);
        printf("swe_houses_ex rc=%d asc=%.6f mc=%.6f\n", rc, ascmc[0], ascmc[1]);
        if (rc == 0) {
            ++passed;
        } else {
            printf("FAIL: swe_houses_ex rc=%d\n", rc);
        }
        if (ascmc[0] >= 0.0 && ascmc[0] < 360.0) {
            ++passed;
        } else {
            printf("FAIL: ascendant out of [0,360)\n");
        }
    }

    /* Cases 8-9: Lahiri ayanamsa (Moshier). */
    {
        double daya = 0.0;
        int32 rc;
        serr[0] = '\0';
        swe_set_sid_mode(SE_SIDM_LAHIRI, 0, 0);
        rc = swe_get_ayanamsa_ex_ut(tjd, SEFLG_MOSEPH, &daya, serr);
        printf("swe_get_ayanamsa_ex_ut rc=%d daya=%.6f serr=%s\n", (int) rc, daya, serr);
        /* Like swe_calc_ut, returns ephemeris flag used (>=0, e.g. 4=MOSEPH); ERR<0 on failure. */
        if (rc >= 0) {
            ++passed;
        } else {
            printf("FAIL: swe_get_ayanamsa_ex_ut rc=%d\n", (int) rc);
        }
        if (daya > 20.0 && daya < 25.0) {
            ++passed;
        } else {
            printf("FAIL: ayanamsa out of (20,25)\n");
        }
    }

    /* Case 10: Moon position, Moshier. */
    {
        double xx[6] = {0};
        int32 rc;
        serr[0] = '\0';
        rc = swe_calc_ut(tjd, SE_MOON, SEFLG_MOSEPH | SEFLG_SPEED, xx, serr);
        printf("swe_calc_ut Moon rc=%d lon=%.6f serr=%s\n", (int) rc, xx[0], serr);
        if (rc >= 0 && xx[0] >= 0.0 && xx[0] < 360.0) {
            ++passed;
        } else {
            printf("FAIL: Moon longitude out of [0,360)\n");
        }
    }

    swe_close();

    printf("swe consumer: %d/%d cases passed\n", passed, discovered);
    {
        int ok = (passed == discovered);
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
               "\"command\":\"test_swe\",\"discovered\":%d,\"passedCount\":%d}\n",
               ok ? "true" : "false", discovered, passed);
        return ok ? 0 : 1;
    }
}
