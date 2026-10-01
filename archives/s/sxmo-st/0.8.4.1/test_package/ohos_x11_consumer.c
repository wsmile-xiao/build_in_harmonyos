/*
 * OHOS consumer test: verify X11/Xft/fontconfig libraries can be consumed
 * by a downstream application (the same APIs that sxmo-st uses).
 *
 * This is NOT an assertion-based test. It exercises real X11/Xft API calls
 * to verify the OHOS-adapted client libraries work correctly as consumers.
 *
 * Since OHOS has no X11 display server, we cannot open a display, but we
 * can verify library linkage, header availability, and API function
 * resolution at the linker level.
 */

#include <X11/Xlib.h>
#include <X11/Xft/Xft.h>
#include <fontconfig/fontconfig.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Exercise X11 library functions to verify they are resolved correctly.
 * On OHOS (no display), we cannot call XOpenDisplay, but we can call
 * functions that don't require a display connection.
 */
static int test_x11_functions(void) {
    /* XInitThreads can be called without a display. */
    XInitThreads();

    /* Verify X11 function pointers are resolved. */
    if (XOpenDisplay(NULL) == NULL) {
        /* Expected on OHOS — no display server. This still proves
         * the function is linked and callable. */
        fprintf(stderr, "  XOpenDisplay: returned NULL (expected on OHOS)\n");
    } else {
        fprintf(stderr, "  XOpenDisplay: succeeded\n");
    }

    fprintf(stderr, "  XInitThreads: PASS\n");
    return 0;
}

/*
 * Exercise FontConfig library functions.
 */
static int test_fontconfig_functions(void) {
    FcConfig *config = FcInitLoadConfigAndFonts();
    if (config == NULL) {
        fprintf(stderr, "  FcInitLoadConfigAndFonts: FAIL\n");
        return 1;
    }

    FcFontSet *fonts = FcFontSetCreate();
    if (fonts == NULL) {
        fprintf(stderr, "  FcFontSetCreate: FAIL\n");
        return 1;
    }

    FcFontSetDestroy(fonts);
    FcConfigDestroy(config);

    fprintf(stderr, "  FontConfig functions: PASS\n");
    return 0;
}

/*
 * Exercise Xft library functions. Xft requires an X display for most
 * operations, but we can verify the library is linked by calling
 * XftInit which only initializes the font config subsystem.
 */
static int test_xft_functions(void) {
    /* XftInit initializes the fontconfig config. Returns Bool: nonzero (True)
     * on success, 0 on failure (X11 init convention). */
    int rc = XftInit(NULL);
    if (rc == 0) {
        fprintf(stderr, "  XftInit: FAIL (rc=%d)\n", rc);
        return 1;
    }

    fprintf(stderr, "  XftInit: PASS\n");
    return 0;
}

int main(void) {
    int rc = 0;

    fprintf(stderr, "=== OHOS X11 Consumer Test ===\n");

    fprintf(stderr, "[1] X11 library functions...\n");
    rc |= test_x11_functions();

    fprintf(stderr, "[2] FontConfig library functions...\n");
    rc |= test_fontconfig_functions();

    fprintf(stderr, "[3] Xft library functions...\n");
    rc |= test_xft_functions();

    if (rc == 0) {
        fprintf(stderr, "=== ALL CONSUMER TESTS PASSED ===\n");
    } else {
        fprintf(stderr, "=== SOME CONSUMER TESTS FAILED ===\n");
    }

    return rc;
}
