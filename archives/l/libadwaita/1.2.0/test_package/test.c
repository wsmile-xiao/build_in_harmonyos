/* HarmonyOS-specific test — verify the libadwaita package is consumable:
 * links against libadwaita-1, and the OHOS adaptation is real (the library
 * exports the Adwaita version API). On OHOS (headless) adw_init() calls
 * gtk_init() which requires a display, so this test deliberately does NOT
 * call adw_init(); it exercises the exported public version functions and
 * the compile-time ADW version macros (a real, observable library call).
 */
#include <adwaita.h>
#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void)
{
    /* Runtime version API — real libadwaita-1 exported functions. */
    CHECK(adw_get_major_version() == ADW_MAJOR_VERSION,
          "adw_get_major_version() == ADW_MAJOR_VERSION");
    CHECK(adw_get_minor_version() == ADW_MINOR_VERSION,
          "adw_get_minor_version() == ADW_MINOR_VERSION");
    CHECK(adw_get_micro_version() == ADW_MICRO_VERSION,
          "adw_get_micro_version() == ADW_MICRO_VERSION");

    /* Compile-time version macros: this package is libadwaita 1.2.0. */
    CHECK(ADW_MAJOR_VERSION == 1 && ADW_MINOR_VERSION == 2 && ADW_MICRO_VERSION == 0,
          "ADW_MAJOR/MINOR/MICRO_VERSION == 1.2.0");
    CHECK(ADW_CHECK_VERSION(1, 2, 0), "ADW_CHECK_VERSION(1,2,0)");

    /* Before adw_init() the library must report not-initialized. */
    CHECK(!adw_is_initialized(), "adw_is_initialized() == FALSE before init");

    if (failures == 0) {
        printf("HARMONY_LIBADWAITA_TEST_PASS: linked libadwaita-1, version API OK\n");
        return 0;
    }
    printf("HARMONY_LIBADWAITA_TEST_FAIL: %d assertion(s) failed\n", failures);
    return 1;
}
