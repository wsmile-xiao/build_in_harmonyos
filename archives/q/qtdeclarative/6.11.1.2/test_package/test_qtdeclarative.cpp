#include <QtQml/QQmlEngine>
#include <QtQml/QQmlComponent>
#include <QtQml/QJSValue>
#include <QtCore/QScopedPointer>
#include <QtCore/QUrl>
#include <QtCore/QVariant>
#include <QtGui/QGuiApplication>
#include <QtQuick/QQuickItem>

#include <cstdio>

/*
 * Substantive smoke test for the Qt Declarative (QML) package on HarmonyOS PC.
 *
 * Creates a QML engine, loads an inline component, instantiates it and
 * evaluates a JavaScript expression through the engine — not a stub.
 */
int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);

    QQmlEngine engine;
    if (engine.rootContext() == nullptr) {
        std::fprintf(stderr, "QQmlEngine::rootContext() returned null\n");
        return 1;
    }

    // Load a minimal inline component and instantiate it.
    QQmlComponent component(&engine);
    component.setData(
        "import QtQuick\n"
        "Item {\n"
        "    property int answer: 42\n"
        "    width: 16\n"
        "    height: 9\n"
        "}\n",
        QUrl());
    if (component.isError()) {
        std::fprintf(stderr, "QML component failed to load: %s\n",
                     qPrintable(component.errorString()));
        return 2;
    }

    QScopedPointer<QObject> object(component.create());
    if (!object) {
        std::fprintf(stderr, "QML component failed to instantiate\n");
        return 3;
    }
    if (qobject_cast<QQuickItem *>(object.data()) == nullptr) {
        std::fprintf(stderr, "QML component did not create a QQuickItem\n");
        return 4;
    }

    const QVariant answer = object->property("answer");
    if (answer.toInt() != 42) {
        std::fprintf(stderr, "QML property 'answer' is not 42\n");
        return 5;
    }

    const QVariant width = object->property("width");
    if (width.toInt() != 16) {
        std::fprintf(stderr, "QQuickItem width is not 16\n");
        return 6;
    }

    // Evaluate a JavaScript expression through the engine.
    const QJSValue result = engine.evaluate("2 + 3 * 4");
    if (result.isError() || result.toInt() != 14) {
        std::fprintf(stderr, "engine.evaluate returned unexpected result\n");
        return 7;
    }

    std::printf("QtDeclarative OK: QtQuick item instantiated, answer=%d, eval=14\n",
                answer.toInt());
    return 0;
}
