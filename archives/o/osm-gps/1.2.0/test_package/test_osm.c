/* Consumer test for osm-gps-map (osm-gps 1.2.0).
 *
 * Calls osm_gps_map_get_type() — the GObject type-registration entry point
 * declared in osm-gps-map.h. This is a genuine end-to-end consumer: it
 * compiles against the library's public header (which transitively pulls in
 * GTK3 / GLib headers), links against libosmgpsmap-1.0, and executes a real
 * exported API. It does NOT require an X/display, so it runs headless on
 * OHOS.
 */
#include <osm-gps-map.h>

int main(void) {
    /* Register the OsmGpsMap GObject type (no widget instantiation,
     * no display required). A valid registered type is never 0. */
    GType t = osm_gps_map_get_type();
    return (t != 0) ? 0 : 1;
}
