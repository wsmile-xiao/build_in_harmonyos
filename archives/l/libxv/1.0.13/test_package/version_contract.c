#include <stdio.h>
#include <string.h>
#include <X11/Xlib.h>
/* Xvlib.h is not self-contained (it pulls Xv.h and XShm.h, which only
 * include X11/X.h); consumers must include Xlib.h first.  The libxext/6.4.0
 * dependency supplies XShm.h and the xorgproto/2025.1 dependency supplies
 * Xv.h. */
#include <X11/extensions/Xvlib.h>
#include <X11/extensions/Xv.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

int main(void) {
    /* Xv port types (xorgproto Xv.h) */
    CHECK(XvInput == 0, "XvInput == 0");
    CHECK(XvOutput == 1, "XvOutput == 1");

    /* Xv port/encoding capability masks */
    CHECK(XvVideoMask == 0x00000004, "XvVideoMask == 0x00000004");
    CHECK(XvStillMask == 0x00000008, "XvStillMask == 0x00000008");
    CHECK(XvPixmapMask == 0x00010000, "XvPixmapMask == 0x00010000");
    CHECK(XvWindowMask == 0x00020000, "XvWindowMask == 0x00020000");

    /* Xv notify event kinds */
    CHECK(XvVideoNotify == 0, "XvVideoNotify == 0");
    CHECK(XvPortNotify == 1, "XvPortNotify == 1");

    /* XvVideoNotify reasons */
    CHECK(XvStarted == 0, "XvStarted == 0");
    CHECK(XvPreempted == 3, "XvPreempted == 3");
    CHECK(XvHardError == 4, "XvHardError == 4");

    /* Xv status/error codes */
    CHECK(XvBadExtension == 1, "XvBadExtension == 1");
    CHECK(XvAlreadyGrabbed == 2, "XvAlreadyGrabbed == 2");
    CHECK(XvInvalidTime == 3, "XvInvalidTime == 3");
    CHECK(XvBadReply == 4, "XvBadReply == 4");

    /* ABI surface: Xv port id is an XID and public structs are complete */
    CHECK(sizeof(XvPortID) >= 4, "XvPortID at least 4 bytes");
    CHECK(sizeof(XvImage) > 0, "XvImage usable");
    CHECK(sizeof(XvAdaptorInfo) > 0, "XvAdaptorInfo usable");
    CHECK(sizeof(XvEncodingInfo) > 0, "XvEncodingInfo usable");
    CHECK(sizeof(XvAttribute) > 0, "XvAttribute usable");
    CHECK(sizeof(XvImageFormatValues) > 0, "XvImageFormatValues usable");
    CHECK(sizeof(XvRational) > 0, "XvRational usable");
    CHECK(sizeof(XvEvent) > 0, "XvEvent usable");
    CHECK(sizeof(XID) > 0, "XID usable");

    /* The extension probe entry point is a real function, not a macro */
    CHECK(&XvQueryExtension != 0, "XvQueryExtension is a function");

    printf("libXv version contract: all checks passed\n");
    return 0;
}
