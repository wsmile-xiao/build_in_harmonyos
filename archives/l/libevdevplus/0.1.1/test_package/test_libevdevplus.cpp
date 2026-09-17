/*
    libevdevplus 消费者测试（Conan L1 / test_package）— 0.1.1

    实质调用被测库 API（R34），不做空壳：
      * InputEvent 构造/拷贝/赋值（libevdevPlus 事件对象）
      * EventDeviceID 构造与 getter（libevdevPlus 设备 ID）
      * EventDevice::IsValidDevice() / Open() 的真实 ioctl 路径（非事件设备 fd）
      * 库导出的键盘映射表（Resource.cpp 的 Table_* 常量）

    设备无关：不需要 /dev/input/eventX，因此可在构建机（含 CI）稳定运行。
    注意：Conan profile 为 Release，NDEBUG 会关掉 assert()，故自带 CHECK 宏，
    不依赖 <cassert>。
*/
#include <evdevPlus/evdevPlus.hpp>

#include <fcntl.h>
#include <unistd.h>

#include <iostream>
#include <stdexcept>
#include <string>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        ++g_checks;                                                        \
        if (!(cond)) {                                                     \
            ++g_failures;                                                  \
            std::cerr << "FAIL: " #cond " (line " << __LINE__ << ")\n";    \
        }                                                                  \
    } while (0)

template <typename Map, typename Key, typename Value>
static bool table_has(const Map &m, const Key &k, const Value &v) {
    typename Map::const_iterator it = m.find(k);
    return it != m.end() && it->second == v;
}

int main() {
    // ── 1. InputEvent：构造 + 字段回读 ──────────────────────────────
    evdevPlus::InputEvent ev(EV_KEY, KEY_A, 1);
    CHECK(ev.Type == EV_KEY);
    CHECK(ev.Code == KEY_A);
    CHECK(ev.Value == 1);

    // ── 2. InputEvent：拷贝构造 / 赋值（结构体语义）────────────────
    evdevPlus::InputEvent copied(ev);
    CHECK(copied.Code == KEY_A);
    CHECK(copied.Value == 1);
    evdevPlus::InputEvent assigned;
    assigned = copied;
    CHECK(assigned.Code == KEY_A);
    CHECK(assigned.Type == EV_KEY);

    // ── 3. EventDeviceID：构造 + getter ────────────────────────────
    evdevPlus::EventDeviceID id(0x0003, 0x046d, 0xc52b, 0x0111);
    CHECK(id.BusType == 0x0003);
    CHECK(id.Vendor == 0x046d);
    CHECK(id.Product == 0xc52b);
    CHECK(id.Version == 0x0111);

    // ── 4. EventDevice：默认状态 + 真实 ioctl 判定路径 ─────────────
    evdevPlus::EventDevice dev;
    CHECK(dev.FD == -1);
    CHECK(dev.EventTypes.empty());

    int fd = ::open("/dev/null", O_RDONLY);
    CHECK(fd >= 0);
    if (fd >= 0) {
        // F_GETFD 成功但 EVIOCGVERSION 失败 → 必须判为"非事件设备"
        CHECK(evdevPlus::EventDevice::IsValidDevice(fd) == false);
        ::close(fd);
    }

    bool threw = false;
    try {
        evdevPlus::EventDevice bad;
        bad.Open(std::string("/dev/null"));
    } catch (const std::runtime_error &) {
        threw = true;
    }
    CHECK(threw);

    // ── 5. 库导出的键盘映射表（Resource.cpp 定义的导出符号）───────
    CHECK(table_has(evdevPlus::Table_ModifierKeys, std::string("SHIFT"), (int)KEY_LEFTSHIFT));
    CHECK(table_has(evdevPlus::Table_FunctionKeys, std::string("F1"), (int)KEY_F1));
    CHECK(table_has(evdevPlus::Table_LowerKeys, 'a', (int)KEY_A));
    CHECK(table_has(evdevPlus::Table_UpperKeys, 'A', (int)KEY_A));
    CHECK(table_has(evdevPlus::Table_KeyCodes, std::string("KEY_A"), (int)KEY_A));
    CHECK(table_has(evdevPlus::Table_KeyCodes, std::string("EV_KEY"), (int)EV_KEY));
    CHECK(evdevPlus::Table_KeyCodes.size() >= 80);

    std::cout << "[test_libevdevplus] checks=" << g_checks
              << " failures=" << g_failures << "\n";
    if (g_failures == 0) {
        std::cout << "[test_libevdevplus] OK\n";
        return 0;
    }
    std::cerr << "[test_libevdevplus] FAILED\n";
    return 1;
}
