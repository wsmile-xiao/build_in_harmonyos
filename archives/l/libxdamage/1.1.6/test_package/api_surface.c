#include <stddef.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xdamage.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libXdamage.so.1 exported API (Xdamage.h) */
DECLARE_SYMBOL(XDamageQueryExtension);
DECLARE_SYMBOL(XDamageQueryVersion);
DECLARE_SYMBOL(XDamageCreate);
DECLARE_SYMBOL(XDamageDestroy);
DECLARE_SYMBOL(XDamageSubtract);
DECLARE_SYMBOL(XDamageAdd);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libXdamage.so.1 fails at link or load
     * time, not silently at runtime. */
    Display *volatile dpy = (Display *)0;
    Damage volatile damage = 0;
    (void)probe_XDamageQueryExtension;
    (void)probe_XDamageQueryVersion;
    (void)probe_XDamageCreate;
    (void)probe_XDamageDestroy;
    (void)probe_XDamageSubtract;
    (void)probe_XDamageAdd;
    if (dpy) { (void)damage; }
    return 0;
}
