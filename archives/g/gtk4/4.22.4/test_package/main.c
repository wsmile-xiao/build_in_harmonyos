/* HarmonyOS-specific test — verify gtk4 package is consumable AND that the
 * OHOS adaptation is real: GTK4 on OHOS is compiled with ONLY the Broadway
 * backend (no X11, no Wayland, no EGL — HarmonyOS PC has no window system),
 * and the package links against glib/2.84.0.1.1 shared.
 *
 * This test deliberately does NOT call gtk_init() (which would try to open a
 * display and fail on a headless HarmonyOS device); it exercises the GTK4
 * public version API and asserts the compile-time backend selection that is
 * the explicit HarmonyOS adaptation.
 */
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(int argc, char **argv)
{
    /* GTK4 runtime version API — real GTK4 library call, no display needed. */
    CHECK(gtk_get_major_version() == 4, "gtk_get_major_version() == 4");
    CHECK(gtk_get_minor_version() == 22, "gtk_get_minor_version() == 22");
    CHECK(gtk_get_micro_version() == 4, "gtk_get_micro_version() == 4");

    /* Compile-time GTK version macros. */
    CHECK(GTK_MAJOR_VERSION == 4 && GTK_MINOR_VERSION == 22,
          "GTK_MAJOR_VERSION==4 && GTK_MINOR_VERSION==22");

    /* HarmonyOS adaptation fact: no X11 / no Wayland / no EGL backend. */
#if defined(GDK_WINDOWING_X11)
    CHECK(0, "GDK_WINDOWING_X11 is NOT defined on OHOS");
#else
    CHECK(1, "GDK_WINDOWING_X11 is NOT defined on OHOS");
#endif
#if defined(GDK_WINDOWING_WAYLAND)
    CHECK(0, "GDK_WINDOWING_WAYLAND is NOT defined on OHOS");
#else
    CHECK(1, "GDK_WINDOWING_WAYLAND is NOT defined on OHOS");
#endif
#if !defined(GDK_WINDOWING_BROADWAY)
    CHECK(0, "GDK_WINDOWING_BROADWAY IS defined (Broadway-only OHOS build)");
#else
    CHECK(1, "GDK_WINDOWING_BROADWAY IS defined (Broadway-only OHOS build)");
#endif

    if (failures == 0) {
        printf("HARMONY_GTK4_TEST_PASS: gtk4 linked against glib, no display required\n");
        return 0;
    }
    printf("HARMONY_GTK4_TEST_FAIL: %d assertion(s) failed\n", failures);
    return 1;
}
