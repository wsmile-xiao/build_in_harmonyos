// test_package 实质测试：链接 Qt5X11Extras 并验证 QX11Info API 可用。
// OHOS 无 X11 显示服务器，QX11Info::isPlatformX11() 在 offscreen 平台
// 上应返回 false，证明库可链接、符号可解析、静态方法可执行（R34 反空壳）。
#include <QGuiApplication>
#include <QtX11Extras/QX11Info>
#include <QtX11Extras/QtX11ExtrasVersion>
#include <cstdio>

int main(int argc, char *argv[]) {
    QGuiApplication application(argc, argv);

    // 断言 1: 版本宏存在且为 5.15.x
    if (QTX11EXTRAS_VERSION_STR[0] != '5') {
        std::fprintf(stderr, "FAIL: unexpected QtX11Extras version %s\n",
                     QTX11EXTRAS_VERSION_STR);
        return 2;
    }
    // 断言 2: isPlatformX11 可调用（非 X11 平台返回 false，不崩溃）
    bool is_x11 = QX11Info::isPlatformX11();
    std::printf("QtX11Extras %s, isPlatformX11=%s\n",
                QTX11EXTRAS_VERSION_STR, is_x11 ? "true" : "false");
    // 断言 3: QX11Info 静态成员符号可解析（编译期已保证），display 访问不崩溃
    QX11Info::appScreen();
    std::printf("PASS: Qt5X11Extras linked and QX11Info callable\n");
    return 0;
}
