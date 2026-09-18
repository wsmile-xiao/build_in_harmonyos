#include <stddef.h>
#include <X11/Xlib.h>
#include <X11/extensions/dmxext.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libdmx.so.1 exported API (dmxext.h) */
DECLARE_SYMBOL(DMXQueryExtension);
DECLARE_SYMBOL(DMXQueryVersion);
DECLARE_SYMBOL(DMXSync);
DECLARE_SYMBOL(DMXForceWindowCreation);
DECLARE_SYMBOL(DMXGetScreenCount);
DECLARE_SYMBOL(DMXGetScreenAttributes);
DECLARE_SYMBOL(DMXChangeScreensAttributes);
DECLARE_SYMBOL(DMXAddScreen);
DECLARE_SYMBOL(DMXRemoveScreen);
DECLARE_SYMBOL(DMXGetWindowAttributes);
DECLARE_SYMBOL(DMXGetDesktopAttributes);
DECLARE_SYMBOL(DMXChangeDesktopAttributes);
DECLARE_SYMBOL(DMXGetInputCount);
DECLARE_SYMBOL(DMXGetInputAttributes);
DECLARE_SYMBOL(DMXAddInput);
DECLARE_SYMBOL(DMXRemoveInput);
DECLARE_SYMBOL(DMXAddBackendInput);
DECLARE_SYMBOL(DMXAddConsoleInput);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libdmx.so.1 fails at link or load time,
     * not silently at runtime. */
    Display *volatile dpy = (Display *)0;
    Window volatile window = 0;
    (void)probe_DMXQueryExtension;
    (void)probe_DMXQueryVersion;
    (void)probe_DMXSync;
    (void)probe_DMXForceWindowCreation;
    (void)probe_DMXGetScreenCount;
    (void)probe_DMXGetScreenAttributes;
    (void)probe_DMXChangeScreensAttributes;
    (void)probe_DMXAddScreen;
    (void)probe_DMXRemoveScreen;
    (void)probe_DMXGetWindowAttributes;
    (void)probe_DMXGetDesktopAttributes;
    (void)probe_DMXChangeDesktopAttributes;
    (void)probe_DMXGetInputCount;
    (void)probe_DMXGetInputAttributes;
    (void)probe_DMXAddInput;
    (void)probe_DMXRemoveInput;
    (void)probe_DMXAddBackendInput;
    (void)probe_DMXAddConsoleInput;
    if (dpy) { (void)window; }
    return 0;
}
