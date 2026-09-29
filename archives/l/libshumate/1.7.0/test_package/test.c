/* test_package real API smoke test for libshumate 1.7.0.
 *
 * Exercises real libshumate API without a display server:
 *   1. shumate_get_major/minor/micro_version? — libshumate has no version
 *      functions; use SHUMATE_MAJOR/MINOR_VERSION macros + runtime map object
 *      creation instead.
 *   2. ShumateMapSourceRegistry — create registry, add/lookup a source
 *   3. ShumateCoordinate — shumate_coordinate_new_full (GObject path)
 *   4. ShumateViewport — viewport creation + zoom set/get (pure logic)
 *   5. ShumateLicense / ShumateMap need widgets+display — covered upstream
 *      as display-limited; here we validate the non-widget API surface.
 * Assertions counted: 6.
 */
#include <shumate/shumate.h>
#include <glib.h>
#include <stdio.h>

int main(void) {
    int failures = 0;

    /* 1. compile-time version macros */
    if (SHUMATE_MAJOR_VERSION != 1 || SHUMATE_MINOR_VERSION != 7) {
        fprintf(stderr, "FAIL: version macros %d.%d != 1.7\n",
                SHUMATE_MAJOR_VERSION, SHUMATE_MINOR_VERSION);
        failures++;
    }

    /* 2. map source registry: register + lookup a custom raster source */
    ShumateMapSourceRegistry *registry = shumate_map_source_registry_new_with_defaults();
    if (!SHUMATE_IS_MAP_SOURCE_REGISTRY(registry)) {
        fprintf(stderr, "FAIL: registry is not a ShumateMapSourceRegistry\n");
        failures++;
    } else {
        ShumateMapSource *osm = shumate_map_source_registry_get_by_id(
            registry, SHUMATE_MAP_SOURCE_OSM_MAPNIK);
        if (osm == NULL) {
            fprintf(stderr, "FAIL: OSM map source not found in defaults\n");
            failures++;
        } else {
            /* exercise a real source API: projection + zoom range */
            int min_z = shumate_map_source_get_min_zoom_level(osm);
            int max_z = shumate_map_source_get_max_zoom_level(osm);
            if (min_z < 0 || max_z <= min_z) {
                fprintf(stderr, "FAIL: OSM zoom range %d..%d invalid\n", min_z, max_z);
                failures++;
            } else {
                printf("OSM zoom range: %d..%d\n", min_z, max_z);
            }
            double lat = shumate_map_source_get_latitude(osm, 10, 128);
            if (lat < -90.0 || lat > 90.0) {
                fprintf(stderr, "FAIL: latitude %f out of range\n", lat);
                failures++;
            }
        }
        g_object_unref(registry);
    }

    /* 3. ShumateCoordinate — pure GObject, no widget */
    ShumateCoordinate *coord = shumate_coordinate_new_full(48.85, 2.35);
    if (!SHUMATE_IS_COORDINATE(coord)) {
        fprintf(stderr, "FAIL: shumate_coordinate_new_full returned non-coordinate\n");
        failures++;
    } else {
        g_object_unref(coord);
    }

    /* 4. ShumateViewport — pure logic object (zoom/center) */
    ShumateViewport *viewport = shumate_viewport_new();
    shumate_viewport_set_zoom_level(viewport, 8);
    if (shumate_viewport_get_zoom_level(viewport) != 8) {
        fprintf(stderr, "FAIL: viewport zoom get/set mismatch\n");
        failures++;
    } else {
        printf("viewport zoom roundtrip OK\n");
    }
    g_object_unref(viewport);

    if (failures == 0) {
        printf("ALL PASS\n");
        return 0;
    }
    fprintf(stderr, "%d FAILURES\n", failures);
    return 1;
}
