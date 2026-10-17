// qt5-qtquickcontrols2 5.15.19 消费者测试执行器。
// 每个用例输出独立的 "TEST <case>: PASS/FAIL" 行，任一用例失败进程以非零码退出。
#include <QQmlEngine>
#include <QQmlComponent>
#include <QCoreApplication>
#include <QDir>
#include <QtQuickControls2/QQuickStyle>
#include <cstdio>
#include <cstdlib>
#include <string>

namespace {

int gPassed = 0;
int gFailed = 0;

void reportCase(const char *name, bool ok, const std::string &detail)
{
    if (ok) {
        ++gPassed;
        std::printf("TEST %s: PASS", name);
    } else {
        ++gFailed;
        std::printf("TEST %s: FAIL", name);
    }
    if (!detail.empty())
        std::printf(" [%s]", detail.c_str());
    std::printf("\n");
}

} // namespace

int main(int argc, char *argv[])
{
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

    // case 1: Qt5QuickControls2 C++ API — QQuickStyle::setStyle + name()。
    // 注：Material/Universal 等带 conf 的风格在无 QGuiApplication（无字体）
    // 环境下初始化 QQuickTheme 会解引用空字体对象——Default 风格无此依赖，
    // 目标机上实测通过。
    QQuickStyle::setStyle("Default");
    const QString styleName = QQuickStyle::name();
    reportCase("case_api_qquickstyle", styleName == QString("Default"),
               "style=" + styleName.toStdString());

    // case 2: QML 模块解析 — import QtQuick.Controls 2.15。
    QQmlComponent component(&engine);
    component.setData(
        "import QtQuick 2.15\n"
        "import QtQuick.Controls 2.15\n"
        "QtObject {}",
        QUrl());
    std::string importDetail;
    if (component.isError()) {
        for (const auto &err : component.errors())
            importDetail += " " + err.toString().toStdString();
    }
    reportCase("case_qml_import", !component.isError(), importDetail);

    // case 3: 端到端 — 实例化组件：QML 插件 .so 实际 dlopen、类型解析、
    // 引擎完成对象创建（消费链路全过程）。
    QObject *root = component.create();
    reportCase("case_e2e_component_create", root != nullptr,
               root ? std::string() : "component.create() returned null");
    delete root;

    std::printf("TEST SUMMARY: %d passed, %d failed\n", gPassed, gFailed);
    return gFailed == 0 ? 0 : 1;
}
