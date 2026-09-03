#include <Kirigami/Platform/Units>

#include <QCoreApplication>
#include <QDebug>
#include <QMetaObject>

namespace
{
int fail(const char *message)
{
    qCritical().noquote() << message;
    return 1;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const QMetaObject &unitsMeta = Kirigami::Platform::Units::staticMetaObject;
    if (unitsMeta.indexOfProperty("gridUnit") < 0 || unitsMeta.indexOfProperty("shortDuration") < 0
        || unitsMeta.indexOfProperty("iconSizes") < 0) {
        return fail("Kirigami Units properties were not exported");
    }

    const QMetaObject &iconSizesMeta = Kirigami::Platform::IconSizes::staticMetaObject;
    if (iconSizesMeta.indexOfMethod("roundedIconSize(int)") < 0) {
        return fail("Kirigami IconSizes invokable was not exported");
    }

    qInfo().noquote() << "PASS: kirigami platform unit meta objects are exported";
    return 0;
}
