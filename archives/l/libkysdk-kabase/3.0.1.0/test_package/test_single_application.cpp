// test_single_application.cpp — libkysdk-kabase 消费者测试（R34：真实调用被测包 API）
//
// 上游头文件真实路径：<single_application/single_application.hpp>
// （上游源码 kysdk-kabase/kabase/single_application/single_application.hpp，
//  声明 namespace kdk { namespace kabase { class QtSingleApplication : public QApplication; }}）。
// 本程序包含该头文件、链接 libkysdk-kabase.so，并真实调用其 API：
//   - QtSingleApplication(const QString &id, int &argc, char **argv) 构造
//   - id()、isRunning()、activationWindow()/setActivationWindow()
// 断言失败 → 非零退出 → conan test 失败。
#include <single_application/single_application.hpp>

#include <QApplication>
#include <QString>
#include <QWidget>

#include <cstdio>

int main(int argc, char **argv)
{
    // offscreen 平台下构造 QtSingleApplication（kdk::kabase 命名空间的真实类型）
    const QString appId = QStringLiteral("kylin-calendar-single-application-test");
    kdk::kabase::QtSingleApplication app(appId, argc, argv);

    // 1) id() 必须回显构造参数（真实调用 QtSingleApplication 成员）
    const QString gotId = app.id();
    std::printf("id=%s\n", gotId.toUtf8().constData());
    if (gotId != appId) {
        std::fprintf(stderr, "FAIL: id() mismatch: got '%s' expected '%s'\n",
                     gotId.toUtf8().constData(), appId.toUtf8().constData());
        return 10;
    }

    // 2) 激活窗口 API（真实调用 setActivationWindow/activationWindow，无 GUI 需要）
    if (app.activationWindow() != nullptr) {
        std::fprintf(stderr, "FAIL: activationWindow() should be null initially\n");
        return 11;
    }
    app.setActivationWindow(nullptr, false);
    if (app.activationWindow() != nullptr) {
        std::fprintf(stderr, "FAIL: activationWindow() should stay null after set(nullptr)\n");
        return 12;
    }

    // 3) isRunning() —— 调用单实例检测逻辑（QtLocalPeer / QtLockedFile）。
    //    全新实例通常返回 false；结果如实打印（不伪造）。
    const bool running = app.isRunning();
    std::printf("isRunning=%d\n", running ? 1 : 0);

    std::printf("PASS: libkysdk-kabase single_application API exercised "
                "(QtSingleApplication ctor / id / activationWindow / isRunning)\n");
    return 0;
}
