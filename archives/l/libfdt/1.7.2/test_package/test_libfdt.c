/* test_libfdt.c — consumer test for libfdt 1.7.2 (R34: real API calls).
 *
 * Exercises the packaged library end to end without shelling out:
 *  1. fdt_create + fdt_finish a minimal in-memory tree (8-byte aligned blob).
 *  2. fdt_check_header must accept the finished blob.
 *  3. fdt_path_offset finds the root node.
 *  4. fdt_setprop_string / fdt_getprop round-trip a "compatible" property.
 *  5. fdt_getprop on a missing property must fail with FDT_ERR_NOTFOUND.
 *  6. fdt_check_header on a zeroed buffer must fail with FDT_ERR_BADMAGIC.
 *  7. fdt_magic distinguishes the valid blob from the zeroed buffer.
 *  8. fdt_strerror returns a non-empty message for FDT_ERR_BADMAGIC.
 *
 * Each CHECK prints PASS and increments the counter (14 checks total);
 * any failure prints FAIL and exits non-zero. The conanfile test()
 * re-emits the count (14) in HMBS_TEST_PACKAGE_RESULT.
 */
#include <stdio.h>
#include <string.h>

#include <libfdt.h>

#define CHECK(cond, label) do { \
    if (!(cond)) { printf("FAIL: %s\n", label); return 1; } \
    printf("PASS: %s\n", label); ++passed; \
} while (0)

int main(void) {
    int passed = 0;
    /* FDT blobs require 8-byte alignment for header access. */
    _Alignas(8) static unsigned char blob[4096];
    _Alignas(8) static unsigned char zerobuf[32];

    memset(blob, 0, sizeof(blob));
    memset(zerobuf, 0, sizeof(zerobuf));

    CHECK(fdt_create(blob, sizeof(blob)) == 0, "fdt_create accepts scratch buffer");
    CHECK(fdt_finish_reservemap(blob) == 0, "fdt_finish_reservemap ok");
    CHECK(fdt_begin_node(blob, "") == 0, "fdt_begin_node root ok");
    CHECK(fdt_property_string(blob, "compatible", "hmbs,libfdt-test") == 0,
          "fdt_property_string compatible ok");
    CHECK(fdt_end_node(blob) == 0, "fdt_end_node ok");
    CHECK(fdt_finish(blob) == 0, "fdt_finish ok");
    CHECK(fdt_check_header(blob) == 0, "fdt_check_header accepts finished blob");
    CHECK(fdt_path_offset(blob, "/") >= 0, "fdt_path_offset root found");

    {
        int len = -1;
        const void *prop = fdt_getprop(blob, 0, "compatible", &len);
        CHECK(prop != NULL && len == (int)strlen("hmbs,libfdt-test") + 1,
              "fdt_getprop compatible length ok");
        CHECK(memcmp(prop, "hmbs,libfdt-test", (size_t)len) == 0,
              "fdt_getprop compatible value round-trip ok");
    }
    {
        int len = 0;
        const void *missing = fdt_getprop(blob, 0, "no-such-prop", &len);
        CHECK(missing == NULL && len == -FDT_ERR_NOTFOUND,
              "fdt_getprop missing property reports FDT_ERR_NOTFOUND");
    }
    CHECK(fdt_check_header(zerobuf) == -FDT_ERR_BADMAGIC,
          "fdt_check_header rejects zeroed buffer with FDT_ERR_BADMAGIC");
    CHECK(fdt_magic(blob) == FDT_MAGIC && fdt_magic(zerobuf) == 0,
          "fdt_magic distinguishes valid blob from zeroed buffer");
    CHECK(fdt_strerror(-FDT_ERR_BADMAGIC) != NULL
          && fdt_strerror(-FDT_ERR_BADMAGIC)[0] != '\0',
          "fdt_strerror returns message for FDT_ERR_BADMAGIC");

    printf("OK: libfdt consumer test %d/14 checks passed\n", passed);
    return (passed == 14) ? 0 : 1;
}
