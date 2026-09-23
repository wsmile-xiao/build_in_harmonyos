#include <stddef.h>
#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xrandr.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

DECLARE_SYMBOL(XRRQueryExtension);
DECLARE_SYMBOL(XRRQueryVersion);
DECLARE_SYMBOL(XRRGetScreenInfo);
DECLARE_SYMBOL(XRRFreeScreenConfigInfo);
DECLARE_SYMBOL(XRRSetScreenConfig);
DECLARE_SYMBOL(XRRSetScreenConfigAndRate);
DECLARE_SYMBOL(XRRConfigTimes);
DECLARE_SYMBOL(XRRConfigSizes);
DECLARE_SYMBOL(XRRConfigRotations);
DECLARE_SYMBOL(XRRConfigCurrentRate);
DECLARE_SYMBOL(XRRConfigCurrentConfiguration);
DECLARE_SYMBOL(XRRRootToScreen);
DECLARE_SYMBOL(XRRSelectInput);
DECLARE_SYMBOL(XRRUpdateConfiguration);
DECLARE_SYMBOL(XRRGetScreenResources);
DECLARE_SYMBOL(XRRGetScreenResourcesCurrent);
DECLARE_SYMBOL(XRRFreeScreenResources);
DECLARE_SYMBOL(XRRGetOutputInfo);
DECLARE_SYMBOL(XRRFreeOutputInfo);
DECLARE_SYMBOL(XRRGetOutputPrimary);
DECLARE_SYMBOL(XRRSetOutputPrimary);
DECLARE_SYMBOL(XRRGetCrtcInfo);
DECLARE_SYMBOL(XRRFreeCrtcInfo);
DECLARE_SYMBOL(XRRSetCrtcConfig);
DECLARE_SYMBOL(XRRGetCrtcGammaSize);
DECLARE_SYMBOL(XRRGetCrtcGamma);
DECLARE_SYMBOL(XRRSetCrtcGamma);
DECLARE_SYMBOL(XRRAllocGamma);
DECLARE_SYMBOL(XRRFreeGamma);
DECLARE_SYMBOL(XRRGetCrtcTransform);
DECLARE_SYMBOL(XRRSetCrtcTransform);
DECLARE_SYMBOL(XRRGetPanning);
DECLARE_SYMBOL(XRRSetPanning);
DECLARE_SYMBOL(XRRFreePanning);
DECLARE_SYMBOL(XRRGetScreenSizeRange);
DECLARE_SYMBOL(XRRSetScreenSize);
DECLARE_SYMBOL(XRRGetProviderInfo);
DECLARE_SYMBOL(XRRFreeProviderInfo);
DECLARE_SYMBOL(XRRGetProviderResources);
DECLARE_SYMBOL(XRRFreeProviderResources);
DECLARE_SYMBOL(XRRGetOutputProperty);
DECLARE_SYMBOL(XRRChangeOutputProperty);
DECLARE_SYMBOL(XRRConfigureOutputProperty);
DECLARE_SYMBOL(XRRQueryOutputProperty);
DECLARE_SYMBOL(XRRListOutputProperties);
DECLARE_SYMBOL(XRRDeleteOutputProperty);
DECLARE_SYMBOL(XRRGetProviderProperty);
DECLARE_SYMBOL(XRRChangeProviderProperty);
DECLARE_SYMBOL(XRRConfigureProviderProperty);
DECLARE_SYMBOL(XRRQueryProviderProperty);
DECLARE_SYMBOL(XRRListProviderProperties);
DECLARE_SYMBOL(XRRDeleteProviderProperty);
DECLARE_SYMBOL(XRRAllocModeInfo);
DECLARE_SYMBOL(XRRFreeModeInfo);
DECLARE_SYMBOL(XRRCreateMode);
DECLARE_SYMBOL(XRRDestroyMode);
DECLARE_SYMBOL(XRRAddOutputMode);
DECLARE_SYMBOL(XRRDeleteOutputMode);
DECLARE_SYMBOL(XRRGetMonitors);
DECLARE_SYMBOL(XRRFreeMonitors);
DECLARE_SYMBOL(XRRSetMonitor);
DECLARE_SYMBOL(XRRAllocateMonitor);
DECLARE_SYMBOL(XRRDeleteMonitor);
DECLARE_SYMBOL(XRRSetProviderOutputSource);
DECLARE_SYMBOL(XRRSetProviderOffloadSink);

#define CHECK_SYMBOL(name) \
    do { \
        if (probe_##name == NULL) { \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    CHECK_SYMBOL(XRRQueryExtension);
    CHECK_SYMBOL(XRRQueryVersion);
    CHECK_SYMBOL(XRRGetScreenInfo);
    CHECK_SYMBOL(XRRFreeScreenConfigInfo);
    CHECK_SYMBOL(XRRSetScreenConfig);
    CHECK_SYMBOL(XRRSetScreenConfigAndRate);
    CHECK_SYMBOL(XRRConfigTimes);
    CHECK_SYMBOL(XRRConfigSizes);
    CHECK_SYMBOL(XRRConfigRotations);
    CHECK_SYMBOL(XRRConfigCurrentRate);
    CHECK_SYMBOL(XRRConfigCurrentConfiguration);
    CHECK_SYMBOL(XRRRootToScreen);
    CHECK_SYMBOL(XRRSelectInput);
    CHECK_SYMBOL(XRRUpdateConfiguration);
    CHECK_SYMBOL(XRRGetScreenResources);
    CHECK_SYMBOL(XRRGetScreenResourcesCurrent);
    CHECK_SYMBOL(XRRFreeScreenResources);
    CHECK_SYMBOL(XRRGetOutputInfo);
    CHECK_SYMBOL(XRRFreeOutputInfo);
    CHECK_SYMBOL(XRRGetOutputPrimary);
    CHECK_SYMBOL(XRRSetOutputPrimary);
    CHECK_SYMBOL(XRRGetCrtcInfo);
    CHECK_SYMBOL(XRRFreeCrtcInfo);
    CHECK_SYMBOL(XRRSetCrtcConfig);
    CHECK_SYMBOL(XRRGetCrtcGammaSize);
    CHECK_SYMBOL(XRRGetCrtcGamma);
    CHECK_SYMBOL(XRRSetCrtcGamma);
    CHECK_SYMBOL(XRRAllocGamma);
    CHECK_SYMBOL(XRRFreeGamma);
    CHECK_SYMBOL(XRRGetCrtcTransform);
    CHECK_SYMBOL(XRRSetCrtcTransform);
    CHECK_SYMBOL(XRRGetPanning);
    CHECK_SYMBOL(XRRSetPanning);
    CHECK_SYMBOL(XRRFreePanning);
    CHECK_SYMBOL(XRRGetScreenSizeRange);
    CHECK_SYMBOL(XRRSetScreenSize);
    CHECK_SYMBOL(XRRGetProviderInfo);
    CHECK_SYMBOL(XRRFreeProviderInfo);
    CHECK_SYMBOL(XRRGetProviderResources);
    CHECK_SYMBOL(XRRFreeProviderResources);
    CHECK_SYMBOL(XRRGetOutputProperty);
    CHECK_SYMBOL(XRRChangeOutputProperty);
    CHECK_SYMBOL(XRRConfigureOutputProperty);
    CHECK_SYMBOL(XRRQueryOutputProperty);
    CHECK_SYMBOL(XRRListOutputProperties);
    CHECK_SYMBOL(XRRDeleteOutputProperty);
    CHECK_SYMBOL(XRRGetProviderProperty);
    CHECK_SYMBOL(XRRChangeProviderProperty);
    CHECK_SYMBOL(XRRConfigureProviderProperty);
    CHECK_SYMBOL(XRRQueryProviderProperty);
    CHECK_SYMBOL(XRRListProviderProperties);
    CHECK_SYMBOL(XRRDeleteProviderProperty);
    CHECK_SYMBOL(XRRAllocModeInfo);
    CHECK_SYMBOL(XRRFreeModeInfo);
    CHECK_SYMBOL(XRRCreateMode);
    CHECK_SYMBOL(XRRDestroyMode);
    CHECK_SYMBOL(XRRAddOutputMode);
    CHECK_SYMBOL(XRRDeleteOutputMode);
    CHECK_SYMBOL(XRRGetMonitors);
    CHECK_SYMBOL(XRRFreeMonitors);
    CHECK_SYMBOL(XRRSetMonitor);
    CHECK_SYMBOL(XRRAllocateMonitor);
    CHECK_SYMBOL(XRRDeleteMonitor);
    CHECK_SYMBOL(XRRSetProviderOutputSource);
    CHECK_SYMBOL(XRRSetProviderOffloadSink);
    puts("LIBXRANDR_TEST api_surface PASS");
    return 0;
}
