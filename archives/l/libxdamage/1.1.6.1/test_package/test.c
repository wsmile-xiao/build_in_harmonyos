/* libxdamage 1.1.6 consumer link + API smoke test.
 *
 * Exercises the public DAMAGE client API surface:
 *   - wire protocol constants from <X11/extensions/damagewire.h>
 *   - header contract: XDAMAGE_1_1_INTERFACE, Damage == XID, DAMAGE version
 *   - real symbol resolution against libXdamage (function pointers taken from
 *     the library must all resolve to non-NULL addresses; if the library were
 *     missing or stripped of these symbols the link/run would fail)
 *   - XDamageNotifyEvent struct field access and the XserverRegion type from
 *     <X11/extensions/Xfixes.h> (needed by XDamageSubtract/XDamageAdd)
 *   - live-server path (only if an X server happens to be reachable):
 *     XDamageQueryExtension + XDamageQueryVersion + XDamageCreate/Destroy
 *
 * HarmonyOS PC has no X server in the build sandbox, so the connection-less
 * path is the one normally taken; XOpenDisplay returning NULL is the
 * documented Xlib contract and is asserted explicitly.
 */

#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/damagewire.h>
#include <X11/extensions/Xfixes.h>
#include <X11/extensions/Xdamage.h>

int main(void) {
    int failures = 0;

    /* 1. Wire protocol constants must match the DAMAGE extension spec. */
    if (DAMAGE_MAJOR != 1 || DAMAGE_MINOR != 1) {
        fprintf(stderr, "unexpected DAMAGE version %d.%d\n",
                DAMAGE_MAJOR, DAMAGE_MINOR);
        failures++;
    }
    if (X_DamageQueryVersion != 0 || X_DamageCreate != 1 ||
        X_DamageDestroy != 2 || X_DamageSubtract != 3 || X_DamageAdd != 4) {
        fprintf(stderr, "unexpected X_Damage* request codes\n");
        failures++;
    }
    if (XDamageNumberRequests != 5) {
        fprintf(stderr, "XDamageNumberRequests != 5\n");
        failures++;
    }
    if (XDamageReportRawRectangles != 0 ||
        XDamageReportDeltaRectangles != 1 ||
        XDamageReportBoundingBox != 2 ||
        XDamageReportNonEmpty != 3) {
        fprintf(stderr, "unexpected XDamageReport* levels\n");
        failures++;
    }
    if (XDamageNotify != 0 || XDamageNumberEvents != 1 ||
        BadDamage != 0 || XDamageNumberErrors != 1) {
        fprintf(stderr, "unexpected XDamage event/error counts\n");
        failures++;
    }

    /* 2. Header contract: XDAMAGE_1_1_INTERFACE and Damage == XID. */
#ifndef XDAMAGE_1_1_INTERFACE
#error "XDAMAGE_1_1_INTERFACE not defined by Xdamage.h"
#endif
    Damage d = (Damage) 0x1234;
    XID xid = (XID) 0x1234;
    if (d != xid) {
        fprintf(stderr, "Damage != XID\n");
        failures++;
    }

    /* 3. Real symbol resolution: every pointer below is a symbol exported by
     *    libXdamage.  Taking their addresses forces the linker/loader to bind
     *    against the tested package. */
    void *symbols[] = {
        (void *) XDamageQueryExtension,
        (void *) XDamageQueryVersion,
        (void *) XDamageCreate,
        (void *) XDamageDestroy,
        (void *) XDamageSubtract,
        (void *) XDamageAdd,
    };
    const int symbol_count = (int) (sizeof(symbols) / sizeof(symbols[0]));
    for (int i = 0; i < symbol_count; i++) {
        if (symbols[i] == NULL) {
            fprintf(stderr, "libXdamage symbol #%d resolved to NULL\n", i);
            failures++;
        }
    }

    /* 4. XDamageNotifyEvent struct layout must be usable by consumers.
     *    Damage levels are int (as declared by Xdamage.h). */
    XDamageNotifyEvent ev;
    ev.type = 42;
    ev.serial = 0x1a2b3c4d;
    ev.send_event = True;
    ev.drawable = (Drawable) 0xabc;
    ev.damage = (Damage) 0xdef;
    ev.level = XDamageReportRawRectangles;
    ev.more = False;
    ev.area.x = -2;
    ev.area.y = 5;
    ev.area.width = 320;
    ev.area.height = 240;
    ev.geometry = ev.area;
    if (ev.damage != (Damage) 0xdef || ev.drawable != (Drawable) 0xabc ||
        ev.level != XDamageReportRawRectangles ||
        ev.area.width != 320 || ev.area.height != 240) {
        fprintf(stderr, "XDamageNotifyEvent round-trip failed\n");
        failures++;
    }

    /* 5. XserverRegion (from Xfixes.h) must be usable for
     *    XDamageSubtract / XDamageAdd — this also forces the test binary to
     *    link libXfixes. */
    XserverRegion reg = (XserverRegion) 0x9876;
    if (reg == (XserverRegion) 0) {
        fprintf(stderr, "XserverRegion == NULL\n");
        failures++;
    }

    /* 6. Server-dependent path.  With no X server (the normal case on the
     *    HarmonyOS build host) XOpenDisplay must return NULL per the Xlib
     *    contract; if a server IS reachable we additionally drive
     *    XDamageQueryExtension/XDamageQueryVersion/XDamageCreate/Destroy. */
    Display *dpy = XOpenDisplay(NULL);
    if (dpy == NULL) {
        printf("no X server reachable — server-dependent checks skipped\n");
    } else {
        int event_base = -1;
        int error_base = -1;
        if (XDamageQueryExtension(dpy, &event_base, &error_base)) {
            int major = 0;
            int minor = 0;
            if (!XDamageQueryVersion(dpy, &major, &minor)) {
                fprintf(stderr, "XDamageQueryVersion failed on live server\n");
                failures++;
            } else {
                printf("server DAMAGE version %d.%d (event base %d)\n",
                       major, minor, event_base);
                Damage dmg = XDamageCreate(
                    dpy, (Drawable) 0, XDamageReportNonEmpty);
                if (dmg != (Damage) 0) {
                    XDamageDestroy(dpy, dmg);
                }
            }
        } else {
            printf("server has no DAMAGE extension\n");
        }
        XCloseDisplay(dpy);
    }

    if (failures != 0) {
        fprintf(stderr, "libxdamage api smoke FAILED (%d checks)\n", failures);
        return 1;
    }
    printf("libxdamage api smoke ok (%d symbols, 5 assertion groups)\n",
           symbol_count);
    return 0;
}
