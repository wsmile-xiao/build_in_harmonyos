#include <Kirigami/Platform/Units>

#include <QCoreApplication>
#include <QDebug>

#include <cstring>
#include <sys/utsname.h>

namespace
{
int fail(const char *message)
{
    qCritical().noquote() << message;
    return 1;
}

bool isHarmonyOsName(const char *name)
{
    return std::strcmp(name, "HarmonyOS") == 0 || std::strcmp(name, "OHOS") == 0;
}

bool isArm64Name(const char *name)
{
    return std::strcmp(name, "aarch64") == 0 || std::strcmp(name, "arm64") == 0;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

#if !defined(__OHOS__)
    return fail("HarmonyOS-specific test was not compiled for __OHOS__");
#endif

    struct utsname host {
    };
    if (uname(&host) != 0) {
        return fail("uname failed on the HarmonyOS PC runtime");
    }
    if (!isHarmonyOsName(host.sysname)) {
        qCritical().noquote() << "unexpected HarmonyOS sysname:" << host.sysname;
        return 1;
    }
    if (!isArm64Name(host.machine)) {
        qCritical().noquote() << "unexpected HarmonyOS machine:" << host.machine;
        return 1;
    }

    const QMetaObject &unitsMeta = Kirigami::Platform::Units::staticMetaObject;
    if (unitsMeta.indexOfProperty("gridUnit") < 0 || unitsMeta.indexOfProperty("iconSizes") < 0) {
        return fail("Kirigami Units API is unavailable on HarmonyOS");
    }

    qInfo().noquote() << "PASS: HarmonyOS" << host.sysname << host.machine
                      << "runs Kirigami Units API";
    return 0;
}
