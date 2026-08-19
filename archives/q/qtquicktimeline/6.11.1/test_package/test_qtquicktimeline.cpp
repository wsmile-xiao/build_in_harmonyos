#include <QtQml/QQmlComponent>
#include <QtQml/QQmlEngine>
#include <QtGui/QGuiApplication>
#include <cstdio>

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);

    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData(
        "import QtQuick.Timeline 6.11\n"
        "import QtQml\n"
        "QtObject {}\n",
        QUrl());
    if (component.isError()) {
        std::fprintf(stderr, "QtQuickTimeline QML import failed: %s\n",
                     qPrintable(component.errorString()));
        return 1;
    }

    std::printf("QtQuickTimeline OK: QtQuick.Timeline module imported and loaded\n");
    return 0;
}
