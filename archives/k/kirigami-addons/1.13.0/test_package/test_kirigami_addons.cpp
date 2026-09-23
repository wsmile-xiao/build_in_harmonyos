#include <KirigamiAddons/Components/NameUtils>
#include <kirigamiaddonscomponents_version.h>

#include <QColor>
#include <QCoreApplication>
#include <QMetaObject>
#include <QString>
#include <cstdio>

namespace
{
int fail(const char *message)
{
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. The ecm_setup_version() header is installed with the devel
    //    component (src/components/CMakeLists.txt install rules) and pins
    //    the packaged upstream release.
    if (QString(KIRIGAMIADDONSCOMPONENTS_VERSION_STRING) != QStringLiteral("1.13.0")) {
        return fail("kirigamiaddonscomponents_version.h reports an unexpected version");
    }
    if (KIRIGAMIADDONSCOMPONENTS_VERSION_MAJOR != 1
            || KIRIGAMIADDONSCOMPONENTS_VERSION_MINOR != 13
            || KIRIGAMIADDONSCOMPONENTS_VERSION_PATCH != 0) {
        return fail("kirigamiaddonscomponents_version.h reports unexpected version parts");
    }

    // 2. NameUtils is the C++ helper backing shipped QML components
    //    (Avatar.qml etc.); exercise both string entry points.
    const QString initials = NameUtils::initialsFromString(QStringLiteral("HarmonyOS PC"));
    if (initials.isEmpty()) {
        return fail("NameUtils::initialsFromString returned an empty result");
    }

    const QColor color = NameUtils::colorsFromString(QStringLiteral("j669539"));
    if (!color.isValid()) {
        return fail("NameUtils::colorsFromString returned an invalid color");
    }

    // 3. The helper class is compiled into libKirigamiAddonsComponents and
    //    must stay exported for the QML plugin to consume it.
    const bool unsuitable = NameUtils::isStringUnsuitableForInitials(QString());
    if (!unsuitable) {
        return fail("empty string should be unsuitable for initials");
    }

    std::printf("PASS kirigami-addons %s initials=%s\n",
                KIRIGAMIADDONSCOMPONENTS_VERSION_STRING, initials.toUtf8().constData());
    return 0;
}
