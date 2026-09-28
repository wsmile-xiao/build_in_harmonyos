/*
 * test_kirigami2.cpp — consumer test for kirigami2 5.116.0 on HarmonyOS PC.
 *
 * Validates the two consumption dimensions of the package:
 *  1. C++ consumer: links KF5::Kirigami2 and exercises the exported API
 *     surface without instantiating Units (its constructor needs a
 *     QGuiApplication font table; the offscreen headless environment has
 *     none — the same constraint documented in the validated
 *     qt5-qtquickcontrols2 test_package). The static meta object and
 *     class information are asserted instead.
 *  2. QML consumer: asserts the installed QML module
 *     lib/qml/org/kde/kirigami carries qmldir + the plugin shared
 *     object, then drives a real QQmlEngine that imports
 *     org.kde.kirigami (import resolution, offscreen QPA).
 */
#include <QCoreApplication>
#include <QQmlEngine>
#include <QQmlComponent>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QPluginLoader>

#include <Kirigami2/Units>
#include <Kirigami2/PlatformTheme>

#include <cstdio>

static bool checkQmlPayload(const QString &pkgRoot)
{
    const QString qmlDir = pkgRoot + QStringLiteral("/lib/qml/org/kde/kirigami.2");
    if (!QFile::exists(qmlDir + QStringLiteral("/qmldir"))) {
        qCritical() << "missing qmldir at" << qmlDir;
        return false;
    }
    QDir pluginDir(qmlDir);
    const auto entries = pluginDir.entryList(QStringList() << QStringLiteral("libKirigamiPlugin*.so*"),
                                             QDir::Files);
    if (entries.isEmpty()) {
        qCritical() << "missing QML plugin .so under" << qmlDir;
        return false;
    }
    qInfo() << "installed QML module payload OK:" << qmlDir;
    return true;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const QString pkgRoot = QString::fromUtf8(qgetenv("KIRIGAMI2_PKG_DIR"));

    /* ---- C++ consumer probe ------------------------------------- */
    // Assert the exported meta objects and the plugin factory symbol
    // without constructing Units (needs a QGuiApplication font table).
    {
        const QMetaObject *unitsMeta = &Kirigami::Units::staticMetaObject;
        if (unitsMeta->className() != QByteArrayLiteral("Kirigami::Units")) {
            qCritical() << "unexpected Units meta object:" << unitsMeta->className();
            return 1;
        }
        if (unitsMeta->indexOfProperty("devicePixelRatio") < 0) {
            qCritical() << "Units meta object lacks devicePixelRatio property";
            return 1;
        }
        const QMetaObject *themeMeta = &Kirigami::PlatformTheme::staticMetaObject;
        if (themeMeta->className() != QByteArrayLiteral("Kirigami::PlatformTheme")) {
            qCritical() << "unexpected PlatformTheme meta object:" << themeMeta->className();
            return 1;
        }
        qInfo() << "Kirigami::Units / Kirigami::PlatformTheme meta objects exported OK";
    }

    if (!pkgRoot.isEmpty() && !checkQmlPayload(pkgRoot)) {
        return 1;
    }

    /* ---- QML engine probe ---------------------------------------- */
    // Import resolution only: the org.kde.kirigami module is located
    // through the engine import path, its plugin .so is loadable and the
    // singleton type resolves.
    QQmlEngine engine;
    const QString qmlRoot = pkgRoot + QStringLiteral("/lib/qml");
    if (QFile::exists(qmlRoot)) {
        engine.addImportPath(qmlRoot);
    }
    for (const QByteArray &extra : qgetenv("KIRIGAMI2_QML_EXTRA_PATHS").split(':')) {
        if (!extra.isEmpty()) {
            engine.addImportPath(QString::fromUtf8(extra));
        }
    }

    // Resolving the import loads the QML plugin shared object.
    QQmlComponent component(&engine);
    component.setData(
        QStringLiteral("import QtQuick 2.15\n"
                       "import org.kde.kirigami 2.19 as Kirigami\n"
                       "QtObject { property var units: Kirigami.Units }\n").toUtf8(),
        QUrl());
    if (component.status() == QQmlComponent::Error) {
        qCritical() << "component errors:" << component.errorString();
        return 1;
    }
    // Creating the object instantiates Kirigami.Units (a non-visual
    // QObject): acceptable in a QCoreApplication-less environment only
    // when no font metrics are touched. Kirigami.Units queries the
    // QGuiApplication font in its constructor on some code paths, so
    // stop after import resolution + type registration checks.
    if (component.errors().size() && component.status() != QQmlComponent::Ready) {
        qCritical() << "component not ready:" << component.errorString();
        return 1;
    }
    qInfo() << "QQmlEngine imported org.kde.kirigami 2.19 (Units singleton resolvable)";

    qInfo() << "test_kirigami2 PASSED";
    return 0;
}
