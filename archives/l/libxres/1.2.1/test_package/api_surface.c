#include <stddef.h>
#include <X11/Xlib.h>
#include <X11/extensions/XRes.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libXRes.so.1 exported API (XRes.h) */
DECLARE_SYMBOL(XResQueryExtension);
DECLARE_SYMBOL(XResQueryVersion);
DECLARE_SYMBOL(XResQueryClients);
DECLARE_SYMBOL(XResQueryClientResources);
DECLARE_SYMBOL(XResQueryClientPixmapBytes);
DECLARE_SYMBOL(XResQueryClientIds);
DECLARE_SYMBOL(XResGetClientIdType);
DECLARE_SYMBOL(XResGetClientPid);
DECLARE_SYMBOL(XResClientIdsDestroy);
DECLARE_SYMBOL(XResQueryResourceBytes);
DECLARE_SYMBOL(XResResourceSizeValuesDestroy);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libXRes.so.1 fails at link or load time,
     * not silently at runtime. */
    Display *volatile dpy = (Display *)0;
    XID volatile xid = 0;
    (void)probe_XResQueryExtension;
    (void)probe_XResQueryVersion;
    (void)probe_XResQueryClients;
    (void)probe_XResQueryClientResources;
    (void)probe_XResQueryClientPixmapBytes;
    (void)probe_XResQueryClientIds;
    (void)probe_XResGetClientIdType;
    (void)probe_XResGetClientPid;
    (void)probe_XResClientIdsDestroy;
    (void)probe_XResQueryResourceBytes;
    (void)probe_XResResourceSizeValuesDestroy;
    if (dpy) { (void)xid; }
    return 0;
}
