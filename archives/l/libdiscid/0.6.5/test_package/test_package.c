/* test_package.c — Conan L1 consumer test for libdiscid.
 *
 * Per R34, this test exercises the libdiscid API beyond a version check:
 *   - discid_get_version_string() returns "libdiscid 0.6.5"
 *   - discid_new() / discid_free() lifecycle
 *   - discid_put() computes the known MusicBrainz DiscID for a fixed TOC
 *   - discid_get_id() / discid_get_freedb_id() match expected values
 *
 * The TOC and expected IDs mirror upstream test/test_put.c, so this consumer
 * test validates the same core calculation path on HarmonyOS (generic platform).
 */
#include <stdio.h>
#include <string.h>
#include "discid/discid.h"

static int tests = 0;
static int passed = 0;

static void check(const char *name, int ok) {
    printf("Testing %s ... %s\n", name, ok ? "OK" : "Failed");
    tests++;
    if (ok) passed++;
}

int main(void) {
    /* 1. Version string */
    const char *ver = discid_get_version_string();
    check("discid_get_version_string non-null", ver != NULL);
    check("version is libdiscid 0.6.5",
          ver != NULL && strcmp(ver, "libdiscid 0.6.5") == 0);

    /* 2. Object lifecycle */
    DiscId *d = discid_new();
    check("discid_new succeeds", d != NULL);

    if (d) {
        /* 3. discid_put with a known 22-track TOC (from upstream test_put.c) */
        int offsets[] = {
            303602,
            150, 9700, 25887, 39297, 53795, 63735, 77517, 94877, 107270,
            123552, 135522, 148422, 161197, 174790, 192022, 205545,
            218010, 228700, 239590, 255470, 266932, 288750,
        };
        int put_ok = discid_put(d, 1, 22, offsets);
        check("discid_put succeeds", put_ok);

        /* 4. Known MusicBrainz DiscID */
        const char *disc_id = discid_get_id(d);
        check("discid_get_id matches expected",
              disc_id != NULL && strcmp(disc_id, "xUp1F2NkfP8s8jaeFn_Av3jNEI4-") == 0);

        /* 5. Known FreeDB DiscID */
        const char *freedb_id = discid_get_freedb_id(d);
        check("discid_get_freedb_id matches expected",
              freedb_id != NULL && strcmp(freedb_id, "370fce16") == 0);

        /* 6. No error after successful put */
        const char *err = discid_get_error_msg(d);
        check("no error after successful put", err != NULL && strlen(err) == 0);

        discid_free(d);
    }
    check("discid_free (no segfault)", 1);

    printf("\n%d tests, %d passed, %d failed\n", tests, passed, tests - passed);
    return passed == tests ? 0 : 1;
}
