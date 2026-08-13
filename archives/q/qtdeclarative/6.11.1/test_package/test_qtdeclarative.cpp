#include <QtQml/QQmlEngine>
#include <QtQml/QQmlComponent>
#include <QtQml/QJSValue>
#include <QtCore/QCoreApplication>

#include <cstdio>

/*
 * Substantive smoke test for the Qt Declarative (QML) package on HarmonyOS PC.
 *
 * Creates a QML engine, loads an inline component, instantiates it and
 * evaluates a JavaScript expression through the engine — not a stub.
 */
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    QQmlEngine engine;
    if (engine.rootContext() == nullptr) {
        std::fprintf(stderr, "QQmlEngine::rootContext() returned null\n");
        return 1;
    }

    // Load a minimal inline component and instantiate it.
    QQmlComponent component(&engine);
    component.setData(
        "import QtQml\n"
        "QtObject {\n"
        "    property int answer: 42\n"
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

    const QVariant answer = object->property("answer");
    if (answer.toInt() != 42) {
        std::fprintf(stderr, "QML property 'answer' is not 42\n");
        return 4;
    }

    // Evaluate a JavaScript expression through the engine.
    const QJSValue result = engine.evaluate("2 + 3 * 4");
    if (result.isError() || result.toInt() != 14) {
        std::fprintf(stderr, "engine.evaluate returned unexpected result\n");
        return 5;
    }

    std::printf("QtDeclarative OK: QML instantiated, answer=%d, eval=14\n",
                answer.toInt());
    return 0;
}
