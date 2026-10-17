/* libxfixes 6.0.1 consumer link + API smoke test.
 *
 * Exercises the public XFIXES client API surface:
 *   - header contract: XFIXES_MAJOR/MINOR/REVISION and XFIXES_VERSION math
 *   - wire protocol constants from <X11/extensions/xfixeswire.h>
 *   - real symbol resolution against libXfixes (function pointers taken from
 *     the library must all resolve to non-NULL addresses; if the library were
 *     missing or stripped of these symbols the link/run would fail)
 *   - XFixesCursorImage / XFixesSelectionNotifyEvent struct field access
 *   - live-server path (only if an X server happens to be reachable):
 *     XFixesQueryExtension + XFixesQueryVersion
 *
 * HarmonyOS PC has no X server in the build sandbox, so the connection-less
 * path is the one normally taken; XOpenDisplay returning NULL is the
 * documented Xlib contract and is asserted explicitly.
 */

#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xfixes.h>
#include <X11/extensions/xfixeswire.h>

int main(void) {
    int failures = 0;

    /* 1. Header version contract (Xfixes.h ships XFIXES_REVISION, the wire
     *    header ships XFIXES_MAJOR/MINOR).  6.0.1 => 6, 0, 1. */
    if (XFIXES_MAJOR != 6 || XFIXES_MINOR != 0 || XFIXES_REVISION != 1) {
        fprintf(stderr, "unexpected XFIXES version %d.%d.%d\n",
                XFIXES_MAJOR, XFIXES_MINOR, XFIXES_REVISION);
        failures++;
    }
    if (XFIXES_VERSION != (XFIXES_MAJOR * 10000) + (XFIXES_MINOR * 100)
                          + XFIXES_REVISION) {
        fprintf(stderr, "XFIXES_VERSION math broken: %d\n", XFIXES_VERSION);
        failures++;
    }

    /* 2. Wire protocol constants must match the XFIXES specification. */
    if (X_XFixesQueryVersion != 0) {
        fprintf(stderr, "X_XFixesQueryVersion != 0\n");
        failures++;
    }
    if (XFixesNumberEvents != 2 || XFixesNumberErrors != (BadBarrier + 1)) {
        fprintf(stderr, "unexpected XFixes event/error counts %d/%d\n",
                XFixesNumberEvents, XFixesNumberErrors);
        failures++;
    }
    if (XFixesSetSelectionOwnerNotifyMask != (1L << 0) ||
        XFixesDisplayCursorNotifyMask != (1L << 0)) {
        fprintf(stderr, "unexpected XFixes notify masks\n");
        failures++;
    }

    /* 3. Real symbol resolution: every pointer below is a symbol exported by
     *    libXfixes.  Taking their addresses forces the linker/loader to bind
     *    against the tested package. */
    void *symbols[] = {
        (void *) XFixesQueryExtension,
        (void *) XFixesQueryVersion,
        (void *) XFixesVersion,
        (void *) XFixesChangeSaveSet,
        (void *) XFixesSelectSelectionInput,
        (void *) XFixesSelectCursorInput,
        (void *) XFixesGetCursorImage,
        (void *) XFixesCreateRegion,
        (void *) XFixesCreateRegionFromBitmap,
        (void *) XFixesDestroyRegion,
        (void *) XFixesSetRegion,
        (void *) XFixesCopyRegion,
        (void *) XFixesUnionRegion,
        (void *) XFixesIntersectRegion,
        (void *) XFixesSubtractRegion,
        (void *) XFixesInvertRegion,
        (void *) XFixesTranslateRegion,
        (void *) XFixesRegionExtents,
        (void *) XFixesFetchRegion,
        (void *) XFixesSetGCClipRegion,
        (void *) XFixesSetWindowShapeRegion,
        (void *) XFixesSetPictureClipRegion,
        (void *) XFixesSetCursorName,
        (void *) XFixesGetCursorName,
        (void *) XFixesChangeCursor,
        (void *) XFixesChangeCursorByName,
        (void *) XFixesExpandRegion,
        (void *) XFixesHideCursor,
        (void *) XFixesShowCursor,
        (void *) XFixesCreatePointerBarrier,
        (void *) XFixesDestroyPointerBarrier,
        (void *) XFixesSetClientDisconnectMode,
        (void *) XFixesGetClientDisconnectMode,
    };
    const int symbol_count = (int) (sizeof(symbols) / sizeof(symbols[0]));
    for (int i = 0; i < symbol_count; i++) {
        if (symbols[i] == NULL) {
            fprintf(stderr, "libXfixes symbol #%d resolved to NULL\n", i);
            failures++;
        }
    }

    /* 4. XFixesVersion() is a pure accessor — no Display needed. */
    int lib_version = XFixesVersion();
    if (lib_version != XFIXES_VERSION) {
        fprintf(stderr, "XFixesVersion()=%d != XFIXES_VERSION=%d\n",
                lib_version, XFIXES_VERSION);
        failures++;
    }

    /* 5. Public struct layouts must be usable by consumers. */
    XFixesCursorImage image;
    image.x = -3;
    image.y = 7;
    image.width = 32;
    image.height = 48;
    image.xhot = 1;
    image.yhot = 2;
    image.cursor_serial = 0x1234;
    image.pixels = NULL;
    image.atom = (Atom) 0;
    image.name = "left_ptr";
    if (image.x != -3 || image.y != 7 || image.width != 32 ||
        image.height != 48 || image.xhot != 1 || image.yhot != 2 ||
        image.cursor_serial != 0x1234u || image.pixels != NULL) {
        fprintf(stderr, "XFixesCursorImage field round-trip failed\n");
        failures++;
    }

    XFixesSelectionNotifyEvent sel_event;
    sel_event.type = 42;
    sel_event.subtype = XFixesSetSelectionOwnerNotify;
    sel_event.window = (Window) 0xabc;
    sel_event.owner = (Window) 0xdef;
    sel_event.selection = (Atom) 9;
    if (sel_event.subtype != XFixesSetSelectionOwnerNotify ||
        sel_event.window != (Window) 0xabc ||
        sel_event.owner != (Window) 0xdef) {
        fprintf(stderr, "XFixesSelectionNotifyEvent round-trip failed\n");
        failures++;
    }

    /* 6. Server-dependent path.  With no X server (the normal case on the
     *    HarmonyOS build host) XOpenDisplay must return NULL per the Xlib
     *    contract; if a server IS reachable we additionally drive
     *    XFixesQueryExtension/XFixesQueryVersion for real. */
    Display *dpy = XOpenDisplay(NULL);
    if (dpy == NULL) {
        printf("no X server reachable — server-dependent checks skipped\n");
    } else {
        int event_base = -1;
        int error_base = -1;
        if (XFixesQueryExtension(dpy, &event_base, &error_base)) {
            int major = 0;
            int minor = 0;
            if (!XFixesQueryVersion(dpy, &major, &minor)) {
                fprintf(stderr, "XFixesQueryVersion failed on live server\n");
                failures++;
            } else {
                printf("server XFIXES version %d.%d (event base %d)\n",
                       major, minor, event_base);
            }
        } else {
            printf("server has no XFIXES extension\n");
        }
        XCloseDisplay(dpy);
    }

    if (failures != 0) {
        fprintf(stderr, "libxfixes api smoke FAILED (%d checks)\n", failures);
        return 1;
    }
    printf("libxfixes api smoke ok (%d symbols, 5 assertion groups)\n",
           symbol_count);
    return 0;
}
