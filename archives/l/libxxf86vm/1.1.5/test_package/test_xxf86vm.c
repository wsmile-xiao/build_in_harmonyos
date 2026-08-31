#include <stddef.h>
#include <X11/Xlib.h>
#include <X11/extensions/xf86vmode.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

DECLARE_SYMBOL(XF86VidModeQueryVersion);
DECLARE_SYMBOL(XF86VidModeQueryExtension);
DECLARE_SYMBOL(XF86VidModeGetAllModeLines);
DECLARE_SYMBOL(XF86VidModeSetClientVersion);
DECLARE_SYMBOL(XF86VidModeGetModeLine);
DECLARE_SYMBOL(XF86VidModeModModeLine);
DECLARE_SYMBOL(XF86VidModeSwitchToMode);
DECLARE_SYMBOL(XF86VidModeSwitchMode);
DECLARE_SYMBOL(XF86VidModeLockModeSwitch);
DECLARE_SYMBOL(XF86VidModeSetViewPort);
DECLARE_SYMBOL(XF86VidModeGetViewPort);
DECLARE_SYMBOL(XF86VidModeGetDotClocks);
DECLARE_SYMBOL(XF86VidModeSetGamma);
DECLARE_SYMBOL(XF86VidModeGetGamma);
DECLARE_SYMBOL(XF86VidModeSetGammaRamp);
DECLARE_SYMBOL(XF86VidModeGetGammaRamp);
DECLARE_SYMBOL(XF86VidModeGetGammaRampSize);
DECLARE_SYMBOL(XF86VidModeGetPermissions);
DECLARE_SYMBOL(XF86VidModeValidateModeLine);
DECLARE_SYMBOL(XF86VidModeAddModeLine);
DECLARE_SYMBOL(XF86VidModeDeleteModeLine);
DECLARE_SYMBOL(XF86VidModeGetMonitor);

#define CHECK_SYMBOL(name) \
    do { \
        if (probe_##name == NULL) { \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    int major = 0, minor = 0;

    CHECK_SYMBOL(XF86VidModeQueryVersion);
    CHECK_SYMBOL(XF86VidModeQueryExtension);
    CHECK_SYMBOL(XF86VidModeGetAllModeLines);
    CHECK_SYMBOL(XF86VidModeSetClientVersion);
    CHECK_SYMBOL(XF86VidModeGetModeLine);
    CHECK_SYMBOL(XF86VidModeModModeLine);
    CHECK_SYMBOL(XF86VidModeSwitchToMode);
    CHECK_SYMBOL(XF86VidModeSwitchMode);
    CHECK_SYMBOL(XF86VidModeLockModeSwitch);
    CHECK_SYMBOL(XF86VidModeSetViewPort);
    CHECK_SYMBOL(XF86VidModeGetViewPort);
    CHECK_SYMBOL(XF86VidModeGetDotClocks);
    CHECK_SYMBOL(XF86VidModeSetGamma);
    CHECK_SYMBOL(XF86VidModeGetGamma);
    CHECK_SYMBOL(XF86VidModeSetGammaRamp);
    CHECK_SYMBOL(XF86VidModeGetGammaRamp);
    CHECK_SYMBOL(XF86VidModeGetGammaRampSize);
    CHECK_SYMBOL(XF86VidModeGetPermissions);
    CHECK_SYMBOL(XF86VidModeValidateModeLine);
    CHECK_SYMBOL(XF86VidModeAddModeLine);
    CHECK_SYMBOL(XF86VidModeDeleteModeLine);
    CHECK_SYMBOL(XF86VidModeGetMonitor);

    /* All 22 public XF86VidMode symbols are resolved by the linker.
       XF86VidModeQueryVersion requires a valid Display* to send an
       X server request; on a headless OHOS device no X server is
       available, so we verify linkage via typed-symbol relocation
       rather than invoking the function with a NULL display pointer
       (which would dereference it and SIGSEGV). */
    (void)major;
    (void)minor;

    return 0;
}
