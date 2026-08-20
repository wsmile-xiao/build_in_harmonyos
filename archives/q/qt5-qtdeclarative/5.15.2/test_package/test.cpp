#include <QQmlEngine>
#include <QQmlComponent>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // 真实调用 Qt5Qml API：创建 QML 引擎并解析一段内联 QML
    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData("import QtQml 2.15; QtObject {}", QUrl());
    if (component.isError()) {
        std::printf("Qt5Qml test FAILED: %s\n",
                    component.errorString().toUtf8().constData());
        return 1;
    }
    std::printf("Qt5Qml test PASSED\n");
    return 0;
}
