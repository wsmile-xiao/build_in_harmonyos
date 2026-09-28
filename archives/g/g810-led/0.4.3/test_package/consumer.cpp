// test_package/consumer.cpp — 消费者验证用例
// 模拟业务上层组件/应用：仅通过 g810-led 安装的公开头文件
// (include/g810-led/Keyboard.h) 与公开链接目标 (libg810-led) 使用该库，
// 调用公开 API 并验证可观察结果。
#include <cstdint>
#include <iostream>
#include <vector>

#include "g810-led/Keyboard.h"

int main() {
    LedKeyboard kbd;
    bool ok = true;

    // 1) 公开 API：listKeyboards() —— 枚举兼容键盘。
    //    本机无兼容键盘时应返回空列表且不崩溃（HID 枚举通道正常初始化）。
    std::vector<LedKeyboard::DeviceInfo> devices = kbd.listKeyboards();
    std::cout << "[consumer] listKeyboards() returned " << devices.size()
              << " device(s)" << std::endl;

    // 2) 公开 API：open() —— 无设备时返回 false（可观察结果），不崩溃。
    bool opened = kbd.open();
    std::cout << "[consumer] open() returned " << (opened ? "true" : "false")
              << std::endl;
    if (opened) {
        kbd.close();
    }

    // 3) 公开 API：commit() —— 未打开设备（unknown 模型）时安全返回 false。
    bool committed = kbd.commit();
    std::cout << "[consumer] commit() returned " << (committed ? "true" : "false")
              << std::endl;

    // 4) 公开 API：Color 结构体构造 + isOpen() 状态查询。
    LedKeyboard::Color color{0xff, 0x00, 0xff};
    bool isOpen = kbd.isOpen();
    std::cout << "[consumer] isOpen() returned " << (isOpen ? "true" : "false")
              << std::endl;

    // 断言：枚举必须可执行（不崩溃）；无硬件时 open/commit/isOpen 均为 false 且一致。
    if (!opened && committed) ok = false;            // 未打开时 commit 必须失败
    if (!opened && isOpen) ok = false;               // 未打开时 isOpen 必须为 false
    if (devices.empty() && opened) ok = false;       // 无设备时 open 必须失败

    std::cout << "[consumer] " << (ok ? "CONSUMER-OK" : "CONSUMER-FAIL") << std::endl;
    return ok ? 0 : 1;
}
