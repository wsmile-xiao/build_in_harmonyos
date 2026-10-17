/*
 * test_kirigami2_harmonyos.cpp — HarmonyOS-specific consumer test.
 *
 * Compiled with the __OHOS__ macro on the HarmonyOS toolchain: asserts
 * the platform identity (uname system/arch), the OHOS compile macro and
 * that the kirigami2 library exports its API for aarch64 OHOS.
 */
#include <Kirigami2/Units>

#include <cstdio>
#include <cstdlib>
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

    // The Units singleton's meta object from the installed KF5Kirigami2
    // shared library must be visible from a plain consumer binary (the
    // constructor is not invoked: it needs a QGuiApplication font table
    // which the headless offscreen environment does not provide).
    const QMetaObject *unitsMeta = &Kirigami::Units::staticMetaObject;
    if (unitsMeta->className() != QByteArrayLiteral("Kirigami::Units")) {
        std::fprintf(stderr, "unexpected Units meta object: %s\n", unitsMeta->className());
        return 1;
    }
    std::printf("HarmonyOS aarch64 links KF5Kirigami2 (Kirigami::Units meta object OK)\n");
    return 0;
}
