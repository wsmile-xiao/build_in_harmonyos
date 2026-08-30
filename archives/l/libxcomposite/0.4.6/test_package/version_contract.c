#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/composite.h>
#include <X11/extensions/Xcomposite.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

/* Live references to libXcomposite.so.1's exported symbols: taking the
 * address forces a real relocation against the built library, so this test is
 * coupled to the .so. If it were dropped by --as-needed, broken, or missing a
 * symbol, the link (or this check) would fail here instead of passing
 * silently. */
#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

DECLARE_SYMBOL(XCompositeQueryExtension);
DECLARE_SYMBOL(XCompositeQueryVersion);
DECLARE_SYMBOL(XCompositeVersion);
DECLARE_SYMBOL(XCompositeRedirectWindow);
DECLARE_SYMBOL(XCompositeRedirectSubwindows);
DECLARE_SYMBOL(XCompositeUnredirectWindow);
DECLARE_SYMBOL(XCompositeUnredirectSubwindows);
DECLARE_SYMBOL(XCompositeCreateRegionFromBorderClip);
DECLARE_SYMBOL(XCompositeNameWindowPixmap);
DECLARE_SYMBOL(XCompositeGetOverlayWindow);
DECLARE_SYMBOL(XCompositeReleaseOverlayWindow);

int main(void) {
    /* COMPOSITE protocol version constants (xorgproto composite.h) */
    CHECK(XCOMPOSITE_MAJOR == COMPOSITE_MAJOR, "XCOMPOSITE_MAJOR == COMPOSITE_MAJOR");
    CHECK(XCOMPOSITE_MINOR == COMPOSITE_MINOR, "XCOMPOSITE_MINOR == COMPOSITE_MINOR");
    CHECK(XCOMPOSITE_MAJOR == 0, "COMPOSITE major == 0");
    CHECK(XCOMPOSITE_MINOR == 4, "COMPOSITE minor == 4");
    CHECK(XCOMPOSITE_VERSION == 402, "XCOMPOSITE_VERSION == (0*10000 + 4*100 + 2)");

    /* Real functional call into libXcomposite.so.1: XCompositeVersion() is
     * exported by the library (src/Xcomposite.c returns XCOMPOSITE_VERSION)
     * and needs no X server, so calling it binds this test to the actual
     * built .so instead of only header constants. */
    CHECK(XCompositeVersion() == 402, "XCompositeVersion() returns 402");

    /* libXcomposite revision constant shipped by the library header */
    CHECK(XCOMPOSITE_REVISION == 2, "XCOMPOSITE_REVISION == 2");

    /* Redirect mode / request selectors from the protocol header */
    CHECK(CompositeRedirectAutomatic == 0, "CompositeRedirectAutomatic == 0");
    CHECK(CompositeRedirectManual == 1, "CompositeRedirectManual == 1");
    CHECK(CompositeNumberRequests == 9, "CompositeNumberRequests == 9");
    CHECK(CompositeNumberEvents == 0, "CompositeNumberEvents == 0");

    /* ABI surface: key types are usable and complete */
    CHECK(sizeof(XserverRegion) > 0, "XserverRegion usable");
    CHECK(sizeof(Pixmap) > 0, "Pixmap usable");
    CHECK(sizeof(Window) > 0, "Window usable");

    /* Live symbols resolved from libXcomposite.so.1 at link time: each probe
     * is a forced relocation, so a broken/empty .so cannot pass here. */
    CHECK(probe_XCompositeQueryExtension != 0, "XCompositeQueryExtension linked");
    CHECK(probe_XCompositeQueryVersion != 0, "XCompositeQueryVersion linked");
    CHECK(probe_XCompositeVersion != 0, "XCompositeVersion linked");
    CHECK(probe_XCompositeRedirectWindow != 0, "XCompositeRedirectWindow linked");
    CHECK(probe_XCompositeRedirectSubwindows != 0, "XCompositeRedirectSubwindows linked");
    CHECK(probe_XCompositeUnredirectWindow != 0, "XCompositeUnredirectWindow linked");
    CHECK(probe_XCompositeUnredirectSubwindows != 0, "XCompositeUnredirectSubwindows linked");
    CHECK(probe_XCompositeCreateRegionFromBorderClip != 0, "XCompositeCreateRegionFromBorderClip linked");
    CHECK(probe_XCompositeNameWindowPixmap != 0, "XCompositeNameWindowPixmap linked");
    CHECK(probe_XCompositeGetOverlayWindow != 0, "XCompositeGetOverlayWindow linked");
    CHECK(probe_XCompositeReleaseOverlayWindow != 0, "XCompositeReleaseOverlayWindow linked");

    printf("libXcomposite version contract: all checks passed\n");
    return 0;
}
