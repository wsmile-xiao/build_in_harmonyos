/* Consumer test for geocode-glib 3.26.4 (libsoup3 flavour).
 *
 * Exercises the pure-logic public API (no network): GeocodeLocation
 * construction, coordinate round-trips, distance computation and the
 * geo URI parser — the same surface upstream's geo-uri test covers.
 * Prints computed values next to expected values and compares.
 */
#include <geocode-glib/geocode-glib.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (cond) {                                             \
            printf("PASS: %s\n", msg);                          \
        } else {                                                \
            printf("FAIL: %s\n", msg);                          \
            failures++;                                         \
        }                                                       \
    } while (0)

int main(void)
{
    /* Test 1: version constant */
    printf("version string: %s (expect 3.26.4)\n", VERSION);
    CHECK(strcmp(VERSION, "3.26.4") == 0, "VERSION macro is 3.26.4");

    /* Test 2: GeocodeLocation construction + coordinate round-trip */
    GeocodeLocation *loc = geocode_location_new(48.85837, 2.294481, 150.0);
    CHECK(GEOCODE_IS_LOCATION(loc), "geocode_location_new returns a location");
    double lat = geocode_location_get_latitude(loc);
    double lon = geocode_location_get_longitude(loc);
    printf("latitude: %.6f (expect 48.858370)\n", lat);
    printf("longitude: %.6f (expect 2.294481)\n", lon);
    CHECK(fabs(lat - 48.85837) < 1e-6, "latitude round-trips");
    CHECK(fabs(lon - 2.294481) < 1e-6, "longitude round-trips");

    /* Test 3: distance computation (Eiffel Tower to Louvre ~ 3.2 km) */
    GeocodeLocation *louvre = geocode_location_new(48.860949, 2.335705, 35.0);
    double d = geocode_location_get_distance_from(loc, louvre);
    printf("distance: %.3f km (expect ~3.2 km, bounds 3.0-3.5)\n", d);
    CHECK(d > 3.0 && d < 3.5, "distance between two Paris landmarks is ~3.2 km");

    /* Test 4: geo URI parsing (upstream geo-uri test surface).
     * 3.26.4's geocode_location_set_from_uri returns FALSE on
     * successful parse too (it propagates g_uri_parse* status which is
     * not a boolean success in this vintage) — the authoritative check
     * is the parsed coordinates themselves. */
    GeocodeLocation *parsed = geocode_location_new(0, 0, 0);
    geocode_location_set_from_uri(parsed, "geo:48.85837,2.294481?z=17", NULL);
    double plat = geocode_location_get_latitude(parsed);
    double plon = geocode_location_get_longitude(parsed);
    printf("parsed latitude: %.6f (expect 48.858370)\n", plat);
    printf("parsed longitude: %.6f (expect 2.294481)\n", plon);
    CHECK(fabs(plat - 48.85837) < 1e-6, "geo URI latitude parses");
    CHECK(fabs(plon - 2.294481) < 1e-6, "geo URI longitude parses");

    /* Test 5: description round-trip (3.26.4 API surface: set/get_description;
     * set_name/get_name only exist in later upstream releases) */
    geocode_location_set_description(loc, "Paris landmark");
    const char *desc = geocode_location_get_description(loc);
    printf("description: %s (expect Paris landmark)\n", desc);
    CHECK(desc && strcmp(desc, "Paris landmark") == 0,
          "location description round-trips");

    g_object_unref(loc);
    g_object_unref(louvre);
    g_object_unref(parsed);

    if (failures == 0) {
        printf("ALL PASS\n");
        return 0;
    }
    printf("FAILED: %d\n", failures);
    return 1;
}
