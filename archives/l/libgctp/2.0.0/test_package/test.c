/*
 * Consumer test for libgctp (USGS GCTPC) 2.0.0.
 *
 * Exercises the public projection API from proj.h as a library user:
 *   - utmforint()/utmfor():  forward UTM projection (lon/lat in radians,
 *     output in meters)
 *   - utminvint()/utminv():  inverse UTM projection
 *
 * Verifiable behavior asserted below:
 *   1. forward projection of the zone-13 central meridian point
 *      (-105 deg, 40 deg) must land on the 500,000 m false easting;
 *   2. the northing must be a physically plausible northern-hemisphere
 *      value around 4,428 km;
 *   3. the inverse round trip must recover the input geodetic coordinates
 *      to within 1e-6 radians (~0.1 m on the ground).
 */
#include <math.h>
#include <stdio.h>
#include "proj.h"

static const double PI = 3.14159265358979323846;

static int failures = 0;

static void check(int cond, const char *what)
{
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

int main(void)
{
    /* WGS84 ellipsoid, UTM zone 13N (central meridian 105 deg W), k0 = 0.9996 */
    const double r_maj = 6378137.0;        /* semi-major axis (m)   */
    const double r_min = 6356752.31424518; /* semi-minor axis (m)   */
    const double scale_fact = 0.9996;
    const long zone = 13;                  /* positive = northern hemisphere */

    const double lon = -105.0 * PI / 180.0;
    const double lat = 40.0 * PI / 180.0;

    double x = 0.0, y = 0.0;
    double lon2 = 0.0, lat2 = 0.0;

    check(utmforint(r_maj, r_min, scale_fact, zone) == 0,
          "utmforint initializes");
    check(utmfor(lon, lat, &x, &y) == 0, "utmfor projects");

    printf("forward UTM 13N (-105E, 40N): easting=%.3f m northing=%.3f m\n",
           x, y);

    /* zone 13 central meridian => false easting of 500,000 m */
    check(fabs(x - 500000.0) < 1.0, "central meridian maps to 500000 m easting");
    /* 40 deg N is roughly 4,428 km from the equator */
    check(y > 4400000.0 && y < 4460000.0, "northing is plausible for 40 deg N");

    check(utminvint(r_maj, r_min, scale_fact, zone) == 0,
          "utminvint initializes");
    check(utminv(x, y, &lon2, &lat2) == 0, "utminv inverts");

    check(fabs(lon2 - lon) < 1e-6 && fabs(lat2 - lat) < 1e-6,
          "inverse round trip recovers input coordinates");

    if (failures == 0) {
        printf("test_libgctp: all assertions passed\n");
        return 0;
    }
    fprintf(stderr, "test_libgctp: %d assertion(s) failed\n", failures);
    return 1;
}
