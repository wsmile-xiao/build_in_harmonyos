#include <QQmlEngine>
#include <QQmlComponent>
#include <QCoreApplication>
#include <QDir>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // Set QML import path to the package's qml/ directory
    const char *qmlImportPath = std::getenv("OHC_QML_IMPORT_PATH");
    if (qmlImportPath) {
        QCoreApplication::addLibraryPath(qmlImportPath);
        QDir::setSearchPaths("qml", QStringList() << qmlImportPath);
    }

    QQmlEngine engine;

    // Attempt to import QtGraphicalEffects — this loads the QML plugin .so
    QQmlComponent component(&engine);
    // Use QtGraphicalEffects 1.15 (the version for Qt 5.15.2)
    component.setData("import QtGraphicalEffects 1.15\nimport QtQuick 2.15\nItem { RectangularGlow { color: '#ff0000' } }",
                       QUrl());
    if (component.isError()) {
        std::printf("QtGraphicalEffects test FAILED:\n");
        for (const auto &err : component.errors()) {
            std::printf("  %s\n", err.toString().toUtf8().constData());
        }
        return 1;
    }

    std::printf("QtGraphicalEffects test PASSED\n");
    return 0;
}
