// Consumer test for kcolorpicker (kColorPicker-Qt6) on HarmonyOS PC.
//
// 按 kImageAnnotator 0.7.2 的真实下游方式消费本库（CMakeLists.txt 见
// find_package(kColorPicker-Qt6 0.3.1 REQUIRED) + kColorPicker::kColorPicker）。
//
// OHOS 适配点覆盖（本 run 适配引入的平台差异）：
//   1. 设备无显示服务器：QApplication 必须跑在 offscreen QPA 上
//      （上游 CI 用 xvfb-run；qtbase/6.11.1 同机 offscreen 先例），
//      断言 platformName() == "offscreen"。
//   2. 共享库 libkColorPicker.so 真实加载：本测试链接的是安装后重签名
//      （E077 四步流程）的 .so —— 能实例化控件即证明 OHOS ELF .codesign
//      签名与运行时链接闭包（Qt6Core/Gui/Widgets）有效。
//   3. Qt Widgets 控件在 offscreen 下可真实实例化、显示、处理事件并
//      完成 API 读写（QColor set/color 往返、resetColors）。

#include <QApplication>
#include <QColor>
#include <QtGlobal>

#include <cstdio>

#include <kColorPicker/KColorPicker.h>

int main(int argc, char **argv)
{
    // 适配点 1：无显示服务器，强制 offscreen QPA
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication application(argc, argv);
    if (application.platformName() != QLatin1String("offscreen"))
        return 1;

    // 适配点 2/3：共享库加载后控件全生命周期（顶层窗口，offscreen 可见）
    kColorPicker::KColorPicker picker(false, nullptr);
    picker.setFixedSize(48, 24);
    picker.show();
    application.processEvents();
    if (!picker.isVisible())
        return 2;

    // API 冒烟：setColor/color 往返
    const QColor expected(0x33, 0x66, 0x99);
    picker.setColor(expected);
    if (picker.color() != expected)
        return 3;

    // resetColors(true) 切换 alpha 通道模式后控件仍可用
    picker.resetColors(true);
    application.processEvents();
    if (!picker.isEnabled())
        return 4;

    std::printf(
        "test_kcolorpicker: KColorPicker OK (offscreen QPA, shared lib loaded)\n");
    return 0;
}
