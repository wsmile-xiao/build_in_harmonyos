#include <stddef.h>
#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xdamage.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

/* Xdamage.h marks the protocol/library interface version with an EMPTY
 * feature macro (#define XDAMAGE_1_1_INTERFACE), so it must be asserted at
 * compile time with #ifdef, not as a runtime boolean expression. */
#ifndef XDAMAGE_1_1_INTERFACE
#error "XDAMAGE_1_1_INTERFACE feature marker missing from Xdamage.h"
#endif

int main(void) {
    /* ABI: Damage is an XID handle */
    CHECK(sizeof(Damage) == sizeof(XID), "Damage is XID-sized");
    CHECK(sizeof(Damage) > 0, "Damage usable");

    /* ABI: XDamageNotifyEvent is a complete usable event struct */
    CHECK(sizeof(XDamageNotifyEvent) > 0, "XDamageNotifyEvent usable");
    CHECK(offsetof(XDamageNotifyEvent, drawable) > offsetof(XDamageNotifyEvent, display),
          "event field order preserved (drawable after display)");
    CHECK(offsetof(XDamageNotifyEvent, area) > offsetof(XDamageNotifyEvent, timestamp),
          "area after timestamp");

    /* Xdamage.h pulls Xfixes.h: XserverRegion must be usable */
    CHECK(sizeof(XserverRegion) > 0, "XserverRegion usable (from Xfixes.h)");

    /* Xlib types used by the API surface */
    CHECK(sizeof(Drawable) > 0, "Drawable usable");
    CHECK(sizeof(XRectangle) > 0, "XRectangle usable");

    printf("libXdamage ABI contract: all checks passed\n");
    return 0;
}
