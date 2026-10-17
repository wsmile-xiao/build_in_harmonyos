#include <stddef.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xvlib.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libXv.so.1 exported API (Xvlib.h, xorgproto Xv.h types) */
DECLARE_SYMBOL(XvQueryExtension);
DECLARE_SYMBOL(XvQueryAdaptors);
DECLARE_SYMBOL(XvQueryEncodings);
DECLARE_SYMBOL(XvFreeAdaptorInfo);
DECLARE_SYMBOL(XvFreeEncodingInfo);
DECLARE_SYMBOL(XvPutVideo);
DECLARE_SYMBOL(XvPutStill);
DECLARE_SYMBOL(XvGetVideo);
DECLARE_SYMBOL(XvGetStill);
DECLARE_SYMBOL(XvStopVideo);
DECLARE_SYMBOL(XvGrabPort);
DECLARE_SYMBOL(XvUngrabPort);
DECLARE_SYMBOL(XvSelectVideoNotify);
DECLARE_SYMBOL(XvSelectPortNotify);
DECLARE_SYMBOL(XvSetPortAttribute);
DECLARE_SYMBOL(XvGetPortAttribute);
DECLARE_SYMBOL(XvQueryBestSize);
DECLARE_SYMBOL(XvQueryPortAttributes);
DECLARE_SYMBOL(XvListImageFormats);
DECLARE_SYMBOL(XvCreateImage);
DECLARE_SYMBOL(XvPutImage);
DECLARE_SYMBOL(XvShmPutImage);
DECLARE_SYMBOL(XvShmCreateImage);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libXv.so.1 fails at link or load time,
     * not silently at runtime. */
    Display *volatile dpy = (Display *)0;
    Drawable volatile draw = 0;
    GC volatile gc = (GC)0;
    (void)probe_XvQueryExtension;
    (void)probe_XvQueryAdaptors;
    (void)probe_XvQueryEncodings;
    (void)probe_XvFreeAdaptorInfo;
    (void)probe_XvFreeEncodingInfo;
    (void)probe_XvPutVideo;
    (void)probe_XvPutStill;
    (void)probe_XvGetVideo;
    (void)probe_XvGetStill;
    (void)probe_XvStopVideo;
    (void)probe_XvGrabPort;
    (void)probe_XvUngrabPort;
    (void)probe_XvSelectVideoNotify;
    (void)probe_XvSelectPortNotify;
    (void)probe_XvSetPortAttribute;
    (void)probe_XvGetPortAttribute;
    (void)probe_XvQueryBestSize;
    (void)probe_XvQueryPortAttributes;
    (void)probe_XvListImageFormats;
    (void)probe_XvCreateImage;
    (void)probe_XvPutImage;
    (void)probe_XvShmPutImage;
    (void)probe_XvShmCreateImage;
    if (dpy) { (void)draw; (void)gc; }
    return 0;
}
