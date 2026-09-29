/*
 * test_kf5windowsystem_harmonyos.cpp — HarmonyOS-specific consumer test.
 *
 * Compiled with the __OHOS__ macro on the HarmonyOS toolchain: asserts the
 * platform identity (uname system/arch) and that kf5windowsystem exports
 * its API for aarch64 OHOS.
 *
 * The OHOS-specific property under test is the absence of any native
 * windowing system: X11 is compiled out and no Wayland platform plugin is
 * published, so KWindowSystem must answer "not X11, not Wayland" instead
 * of resolving a backend (the dummy backend then serves every call).
 */
#include <KWindowSystem>

#include <cstdio>
#include <string>

#if defined(__OHOS__)
#include <sys/utsname.h>
#endif

int main()
{
#if defined(__OHOS__)
    struct utsname buf;
    if (uname(&buf) != 0) {
        std::fprintf(stderr, "uname() failed\n");
        return 1;
    }
    const std::string sysname = buf.sysname;
    // HarmonyOS PC kernels report "HarmonyOS" (or "OHOS" on community
    // builds); accept both, reject Linux/desktop values.
    if (sysname.find("HarmonyOS") == std::string::npos
        && sysname.find("OpenHarmony") == std::string::npos
        && sysname.find("OHOS") == std::string::npos) {
        std::fprintf(stderr, "unexpected sysname: %s\n", sysname.c_str());
        return 1;
    }
#if defined(__aarch64__)
    const std::string machine = buf.machine;
    if (machine != "aarch64") {
        std::fprintf(stderr, "unexpected machine: %s\n", machine.c_str());
        return 1;
    }
#endif
    std::printf("__OHOS__ defined, sysname=%s machine=%s\n", sysname.c_str(), buf.machine);
#else
    std::printf("not built for OHOS; skipping platform assertions\n");
#endif

    // The class meta object exported by the installed libKF5WindowSystem.so
    // must be visible from a plain consumer binary.
    const QMetaObject *meta = &KWindowSystem::staticMetaObject;
    if (meta->className() != QByteArrayLiteral("KWindowSystem")) {
        std::fprintf(stderr, "unexpected KWindowSystem meta object: %s\n", meta->className());
        return 1;
    }

    // OHOS has no X11/Wayland stack: the probe must not claim either
    // backend (KWindowSystem::platform() itself is exercised in the
    // generic consumer test, which runs under the offscreen QPA).
    if (KWindowSystem::isPlatformX11() || KWindowSystem::isPlatformWayland()) {
        std::fprintf(stderr, "unexpected platform: x11=%d wayland=%d\n",
                     int(KWindowSystem::isPlatformX11()),
                     int(KWindowSystem::isPlatformWayland()));
        return 1;
    }

    std::printf("HarmonyOS aarch64 links kf5windowsystem (KWindowSystem meta object OK, no native backend)\n");
    return 0;
}
