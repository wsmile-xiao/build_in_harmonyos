/* test_libfdisk.c — libfdisk 2.42.3 installed-package consumer test.
 *
 * Exercises real libfdisk APIs without requiring a block device:
 * version query, context lifecycle, label enumeration, partition and
 * table objects, script object. Every CHECK runs a library call; any
 * failure returns non-zero (R34 anti-shell: no printf-only pass).
 */
#include <stdio.h>
#include <string.h>

#include <libfdisk/libfdisk.h>

static int g_checks = 0;
static int g_passed = 0;

#define CHECK(cond, name) do { \
    g_checks++; \
    if (cond) { g_passed++; printf("PASS: %s\n", name); } \
    else { printf("FAIL: %s\n", name); } \
} while (0)

int main(void)
{
    const char *ver = NULL;
    const char **features = NULL;
    struct fdisk_context *cxt = NULL;
    struct fdisk_partition *pa = NULL;
    struct fdisk_table *tb = NULL;
    struct fdisk_script *dp = NULL;
    struct fdisk_label *lb = NULL;
    size_t nlabels = 0;

    /* 1: library version query (returns version code > 0, not 0;
       see libfdisk/src/version.c: fdisk_get_library_version returns
       fdisk_parse_version_string(LIBFDISK_VERSION), e.g. 2423) */
    CHECK(fdisk_get_library_version(&ver) > 0 && ver != NULL && ver[0] != '\0',
          "get_library_version returns version code and non-empty string");
    if (ver)
        printf("INFO: libfdisk version: %s\n", ver);
    CHECK(ver != NULL && strstr(ver, "2.42.3") != NULL,
          "version string contains 2.42.3");

    /* 2: version parse helper */
    CHECK(fdisk_parse_version_string("2.42.3") > 0,
          "parse_version_string accepts 2.42.3");

    /* 3: feature list query (returns feature count >= 0, not 0;
       see libfdisk/src/version.c: fdisk_get_library_features returns
       ARRAY_SIZE(lib_features)-1, i.e. 1-2; must also set pointer) */
    CHECK(fdisk_get_library_features(&features) >= 0 && features != NULL,
          "get_library_features succeeds");

    /* 4: context lifecycle */
    cxt = fdisk_new_context();
    CHECK(cxt != NULL, "new_context returns handler");
    if (cxt == NULL) {
        printf("SUMMARY: %d/%d passed\n", g_passed, g_checks);
        return 1;
    }

    /* 5: compiled-in label drivers enumerable without a device */
    nlabels = fdisk_get_nlabels(cxt);
    CHECK(nlabels > 0, "get_nlabels reports at least one label driver");
    printf("INFO: nlabels=%u\n", (unsigned)nlabels);
    CHECK(fdisk_next_label(cxt, &lb) == 0 && lb != NULL,
          "next_label iterates to first driver");

    /* 6: partition object with start/size round-trip */
    pa = fdisk_new_partition();
    CHECK(pa != NULL, "new_partition returns object");
    if (pa != NULL) {
        int ok = 0;
        ok |= fdisk_partition_set_start(pa, 2048);
        ok |= fdisk_partition_set_size(pa, 100000);
        CHECK(ok == 0, "partition set_start/set_size succeed");
        CHECK(fdisk_partition_get_start(pa) == 2048,
              "partition start round-trips");
        CHECK(fdisk_partition_get_size(pa) == 100000,
              "partition size round-trips");
        fdisk_unref_partition(pa);
    }

    /* 7: table object starts empty */
    tb = fdisk_new_table();
    CHECK(tb != NULL, "new_table returns object");
    if (tb != NULL) {
        CHECK(fdisk_table_is_empty(tb) == 1, "new table is empty");
        fdisk_unref_table(tb);
    }

    /* 8: script object lifecycle bound to context */
    dp = fdisk_new_script(cxt);
    CHECK(dp != NULL, "new_script returns object");
    if (dp != NULL)
        fdisk_unref_script(dp);

    fdisk_unref_context(cxt);

    printf("SUMMARY: %d/%d passed\n", g_passed, g_checks);
    return (g_passed == g_checks) ? 0 : 1;
}
