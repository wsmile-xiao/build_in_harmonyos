/*
 * libXcursor ABI contract test.
 *
 * Pins the version macros, the public struct layouts (offsetof, so the checks
 * stay correct on both 32- and 64-bit targets), and the exported function
 * signatures via typed function-pointer assignment (a real compile-time check
 * under -Werror, not a runtime sizeof() no-op).
 */

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <X11/Xcursor/Xcursor.h>

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (!(cond)) {                                       \
            fprintf(stderr, "FAIL: %s\n", msg);              \
            return 1;                                        \
        }                                                    \
    } while (0)

/* --- compile-time signature contracts (typed assignment) --- */
static XcursorImage *(*const sig_ImageCreate)(int, int) = XcursorImageCreate;
static void (*const sig_ImageDestroy)(XcursorImage *) = XcursorImageDestroy;
static Cursor (*const sig_ImageLoadCursor)(Display *, const XcursorImage *) =
    XcursorImageLoadCursor;
static XcursorBool (*const sig_SetTheme)(Display *, const char *) = XcursorSetTheme;
static char *(*const sig_GetTheme)(Display *) = XcursorGetTheme;
static XcursorBool (*const sig_SetThemeCore)(Display *, XcursorBool) = XcursorSetThemeCore;
static int (*const sig_GetDefaultSize)(Display *) = XcursorGetDefaultSize;
static XcursorBool (*const sig_SupportsARGB)(Display *) = XcursorSupportsARGB;
static XcursorBool (*const sig_SupportsAnim)(Display *) = XcursorSupportsAnim;
static const char *(*const sig_LibraryPath)(void) = XcursorLibraryPath;

int main(void)
{
    (void)sig_ImageCreate;
    (void)sig_ImageDestroy;
    (void)sig_ImageLoadCursor;
    (void)sig_SetTheme;
    (void)sig_GetTheme;
    (void)sig_SetThemeCore;
    (void)sig_GetDefaultSize;
    (void)sig_SupportsARGB;
    (void)sig_SupportsAnim;
    (void)sig_LibraryPath;

    /* --- version contract --- */
    CHECK(XCURSOR_LIB_MAJOR == 1, "XCURSOR_LIB_MAJOR == 1");
    CHECK(XCURSOR_LIB_MINOR == 2, "XCURSOR_LIB_MINOR == 2");
    CHECK(XCURSOR_LIB_REVISION == 3, "XCURSOR_LIB_REVISION == 3");
    CHECK(XCURSOR_LIB_VERSION == 10203, "XCURSOR_LIB_VERSION == 10203");

    /* --- scalar ABI types --- */
    CHECK(sizeof(XcursorUInt) == sizeof(uint32_t), "XcursorUInt is uint32_t");
    CHECK(sizeof(XcursorDim) == sizeof(XcursorUInt), "XcursorDim is XcursorUInt");
    CHECK(sizeof(XcursorPixel) == sizeof(XcursorUInt), "XcursorPixel is XcursorUInt");
    CHECK(sizeof(XcursorBool) == sizeof(int), "XcursorBool is int");

    /* --- XcursorImage layout: 7 CARD32 fields then a pixels pointer --- */
    CHECK(offsetof(XcursorImage, version) == 0, "XcursorImage.version at 0");
    CHECK(offsetof(XcursorImage, size) == 4 * 1, "XcursorImage.size at 4");
    CHECK(offsetof(XcursorImage, width) == 4 * 2, "XcursorImage.width at 8");
    CHECK(offsetof(XcursorImage, height) == 4 * 3, "XcursorImage.height at 12");
    CHECK(offsetof(XcursorImage, xhot) == 4 * 4, "XcursorImage.xhot at 16");
    CHECK(offsetof(XcursorImage, yhot) == 4 * 5, "XcursorImage.yhot at 20");
    CHECK(offsetof(XcursorImage, delay) == 4 * 6, "XcursorImage.delay at 24");
    /* pixels is a pointer so it is 8-byte aligned on LP64 (offset 32) but
     * only 4-byte aligned on ILP32 (offset 28): assert the bound, then pin the
     * total size with the alignment-independent sizeof relation below. */
    CHECK(offsetof(XcursorImage, pixels) >= 4 * 7,
          "XcursorImage.pixels after all 7 CARD32 fields");
    CHECK(sizeof(XcursorImage) == offsetof(XcursorImage, pixels) + sizeof(XcursorPixel *),
          "XcursorImage size = 7*CARD32 + pixels pointer");

    /* --- XcursorImages: nimage then two pointers --- */
    CHECK(offsetof(XcursorImages, nimage) == 0, "XcursorImages.nimage at 0");
    CHECK(sizeof(XcursorImages) == offsetof(XcursorImages, name) + sizeof(char *),
          "XcursorImages size ends at name pointer");

    /* --- XcursorFile: closure + 3 callback pointers --- */
    CHECK(offsetof(XcursorFile, closure) == 0, "XcursorFile.closure at 0");
    CHECK(offsetof(XcursorFile, read) == sizeof(void *),
          "XcursorFile.read after closure");
    CHECK(offsetof(XcursorFile, seek) == 3 * sizeof(void *),
          "XcursorFile.seek after write");
    CHECK(sizeof(XcursorFile) == 4 * sizeof(void *),
          "XcursorFile is 4 pointer-sized fields");

    /* --- XcursorCursors: { Display *dpy; int ref; int ncursor; Cursor *cursors; } --- */
    CHECK(offsetof(XcursorCursors, dpy) == 0, "XcursorCursors.dpy at 0");
    CHECK(offsetof(XcursorCursors, cursors) >= offsetof(XcursorCursors, ncursor) + sizeof(int),
          "XcursorCursors.cursors after ncursor int");
    /* cursors is the last member and is pointer-aligned, so the struct has no
     * trailing padding on either ILP32 or LP64. */
    CHECK(sizeof(XcursorCursors) == offsetof(XcursorCursors, cursors) + sizeof(Cursor *),
          "XcursorCursors size ends at cursors array");

    printf("libXcursor ABI contract: all checks passed\n");
    return 0;
}
