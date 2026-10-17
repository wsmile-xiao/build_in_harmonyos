#include <Kirigami/Platform/Units>

#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QGuiApplication>
#include <QMetaObject>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QStringList>
#include <QUrl>

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
    QGuiApplication app(argc, argv);

    // 1) C++ consumer: the public Kirigami C++ classes are exported.
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

    // 2) Installed QML module payload: qmldir + plugin shared object.
    const QString qmlRoot = qEnvironmentVariable("KIRIGAMI_QML_DIR");
    if (qmlRoot.isEmpty()) {
        return fail("KIRIGAMI_QML_DIR is not set");
    }
    const QString moduleDir = qmlRoot + QStringLiteral("/org/kde/kirigami");
    if (!QFileInfo::exists(moduleDir + QStringLiteral("/qmldir"))) {
        return fail("installed QML module org.kde.kirigami has no qmldir");
    }
    const QStringList plugins = QDir(moduleDir).entryList(QStringList() << QStringLiteral("*.so"), QDir::Files);
    if (plugins.isEmpty()) {
        return fail("installed QML module org.kde.kirigami has no plugin shared object");
    }
    qInfo().noquote() << "PASS: installed QML module payload" << moduleDir
                      << "contains qmldir and" << plugins.join(QStringLiteral(", "));

    // 3) Real QML engine: import org.kde.kirigami and instantiate a type.
    QQmlEngine engine;
    engine.addImportPath(qmlRoot);
    QQmlComponent component(&engine);
    component.setData(
        "import QtQuick\n"
        "import org.kde.kirigami as Kirigami\n"
        "Kirigami.Heading { text: \"kirigami-qml-ok\" }\n",
        QUrl(QStringLiteral("qrc:/kirigami-qml-probe.qml")));
    if (component.isError()) {
        qCritical().noquote() << component.errors();
        return fail("QQmlComponent failed to import org.kde.kirigami");
    }
    QObject *object = component.create();
    if (!object) {
        qCritical().noquote() << component.errors();
        return fail("org.kde.kirigami type could not be instantiated");
    }
    qInfo().noquote() << "PASS: QQmlEngine imported org.kde.kirigami and instantiated"
                      << object->metaObject()->className();
    delete object;

    return 0;
}
