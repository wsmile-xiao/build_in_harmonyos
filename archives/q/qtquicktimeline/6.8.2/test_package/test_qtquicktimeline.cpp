#include <QtCore/QUrl>
#include <QtGui/QGuiApplication>
#include <QtQml/QQmlComponent>
#include <QtQml/QQmlEngine>

#include <iostream>

int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    QQmlEngine engine;
    engine.addImportPath(QLatin1String("qrc:/qt/qml"));
    QQmlComponent component(&engine);
    component.setData(R"QML(
import QtQuick
import QtQuick.Timeline

Timeline {
    enabled: true
}
)QML", QUrl());

    if (component.isError()) {
        const auto errors = component.errors();
        for (const auto &error : errors) {
            std::cerr << error.toString().toStdString() << std::endl;
        }
        return 1;
    }

    QObject *object = component.create();
    if (object == nullptr) {
        return 1;
    }
    delete object;
    return 0;
}
