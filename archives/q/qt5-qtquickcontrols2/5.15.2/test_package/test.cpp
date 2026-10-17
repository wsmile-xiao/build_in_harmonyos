#include <QQmlEngine>
#include <QQmlComponent>
#include <QCoreApplication>
#include <QDir>
#include <QtQuickControls2/QQuickStyle>
#include <cstdio>
#include <string>

int main(int argc, char *argv[]) {
    // 注意：不创建窗口、不触发平台插件加载，QCoreApplication 足够——
    // 交叉测试环境无 X server，避免 QGuiApplication 初始化 platform plugin。
    QCoreApplication app(argc, argv);

    QQmlEngine engine;

    // Register QML import paths (colon-separated). QCoreApplication::
    // addLibraryPath does NOT extend the QML engine's import path list,
    // engine.addImportPath() is the correct way (verified on target).
    const char *qmlImportPath = std::getenv("OHC_QML_IMPORT_PATH");
    if (qmlImportPath) {
        for (const QString &one :
             QString::fromLocal8Bit(qmlImportPath).split(":")) {
            if (!one.isEmpty()) {
                engine.addImportPath(one);
            }
        }
    }

    // 真实调用 Qt5QuickControls2 C++ API：QQuickStyle::setStyle(Default)。
    // 注：Material/Universal 等带 conf 的风格在无 QGuiApplication（无字体）
    // 环境下初始化 QQuickTheme 会解引用空字体对象——Default 风格无此依赖，
    // 目标机上实测通过（b3 验证）；可视化控件实例化同样需要字体，故 QML
    // 侧验证到「import QtQuick.Controls 2.15 + create QtObject」层级。
    QQuickStyle::setStyle("Default");
    if (QQuickStyle::name() != QString("Default")) {
        std::printf("QtQuickControls2 test FAILED: style name mismatch\n");
        return 1;
    }

    // Attempt to import QtQuick.Controls 2 — this loads the QML plugin .so
    // (qtquickcontrols2plugin) and resolves the QtQuick.Controls module.
    QQmlComponent component(&engine);
    component.setData(
        "import QtQuick 2.15\n"
        "import QtQuick.Controls 2.15\n"
        "QtObject {}",
        QUrl());
    if (component.isError()) {
        std::printf("QtQuickControls2 test FAILED:\n");
        for (const auto &err : component.errors()) {
            std::printf("  %s\n", err.toString().toUtf8().constData());
        }
        return 1;
    }
    QObject *root = component.create();
    if (!root) {
        std::printf("QtQuickControls2 test FAILED: component.create() null\n");
        return 1;
    }

    std::printf("QtQuickControls2 test PASSED (style=%s, import+create OK)\n",
                QQuickStyle::name().toUtf8().constData());
    return 0;
}
