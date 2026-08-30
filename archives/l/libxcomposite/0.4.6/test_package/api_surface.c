#include <stddef.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xcomposite.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libXcomposite.so.1 exported API (Xcomposite.h) */
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
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libXcomposite.so.1 fails at link or load
     * time, not silently at runtime. */
    Display *volatile dpy = (Display *)0;
    Window volatile win = 0;
    (void)probe_XCompositeQueryExtension;
    (void)probe_XCompositeQueryVersion;
    (void)probe_XCompositeVersion;
    (void)probe_XCompositeRedirectWindow;
    (void)probe_XCompositeRedirectSubwindows;
    (void)probe_XCompositeUnredirectWindow;
    (void)probe_XCompositeUnredirectSubwindows;
    (void)probe_XCompositeCreateRegionFromBorderClip;
    (void)probe_XCompositeNameWindowPixmap;
    (void)probe_XCompositeGetOverlayWindow;
    (void)probe_XCompositeReleaseOverlayWindow;
    if (dpy) { (void)win; }
    return 0;
}
