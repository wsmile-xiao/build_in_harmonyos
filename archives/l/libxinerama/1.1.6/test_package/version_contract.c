#include <stddef.h>
#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xinerama.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

int main(void) {
    /* ABI contract: XineramaScreenInfo struct layout is part of the public
     * Xinerama API consumed by window managers and compositors.  Any change
     * to these offsets breaks ABI, so pin them explicitly. */
    CHECK(sizeof(XineramaScreenInfo) == 12, "sizeof(XineramaScreenInfo) == 12");
    CHECK(offsetof(XineramaScreenInfo, screen_number) == 0, "offset screen_number == 0");
    CHECK(offsetof(XineramaScreenInfo, x_org) == 4, "offset x_org == 4");
    CHECK(offsetof(XineramaScreenInfo, y_org) == 6, "offset y_org == 6");
    CHECK(offsetof(XineramaScreenInfo, width) == 8, "offset width == 8");
    CHECK(offsetof(XineramaScreenInfo, height) == 10, "offset height == 10");

    /* Field types are fixed-size and usable */
    CHECK(sizeof(((XineramaScreenInfo *)0)->screen_number) == sizeof(int), "screen_number is int");
    CHECK(sizeof(((XineramaScreenInfo *)0)->x_org) == sizeof(short), "x_org is short");
    CHECK(sizeof(((XineramaScreenInfo *)0)->width) == sizeof(short), "width is short");

    /* Header is self-contained against Xlib types (Display is opaque in the
     * public headers; the pointer and the Status handle are the ABI surface) */
    CHECK(sizeof(Display *) == sizeof(void *), "Display pointer is void*-sized");
    CHECK(sizeof(Status) > 0, "Status usable from Xlib");

    printf("libXinerama ABI contract: all checks passed\n");
    return 0;
}
