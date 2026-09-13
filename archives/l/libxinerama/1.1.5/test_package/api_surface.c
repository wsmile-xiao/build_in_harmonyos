#include <stddef.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xinerama.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libXinerama.so.1 exported API (Xinerama.h) */
DECLARE_SYMBOL(XineramaQueryExtension);
DECLARE_SYMBOL(XineramaQueryVersion);
DECLARE_SYMBOL(XineramaIsActive);
DECLARE_SYMBOL(XineramaQueryScreens);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libXinerama.so.1 fails at link or load
     * time, not silently at runtime. */
    Display *volatile dpy = (Display *)0;
    int volatile number = 0;
    (void)probe_XineramaQueryExtension;
    (void)probe_XineramaQueryVersion;
    (void)probe_XineramaIsActive;
    (void)probe_XineramaQueryScreens;
    if (dpy) { (void)number; }
    return 0;
}
