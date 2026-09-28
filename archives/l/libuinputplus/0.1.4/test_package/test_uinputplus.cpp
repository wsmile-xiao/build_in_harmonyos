// test_package/test_uinputplus.cpp
// Consumer-level test for libuinputplus 0.1.4.
//
// The real-device path (open("/dev/uinput") + ioctls) cannot run on a build
// machine, so this test drives the documented callback mode
// (uInput::Init(callback, userp)): Emit() then invokes our callback instead
// of writing to the device, making the whole emit pipeline observable
// without any /dev/uinput access.
#include <cstdio>
#include <cstdint>
#include <vector>

#include "uInput.hpp"
#include "uInputSetup.hpp"
#include "CommonIncludes.hpp"

using namespace uInputPlus;

namespace {

struct Event {
    uint16_t type;
    uint16_t code;
    int32_t value;
};

std::vector<Event> g_events;
int g_failures = 0;

int record_event(uint16_t type, uint16_t code, int32_t value, void *userp) {
    (void)userp;
    Event e{};
    e.type = type;
    e.code = code;
    e.value = value;
    g_events.push_back(e);
    return 0;
}

void expect(bool cond, const char *what) {
    if (!cond) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        ++g_failures;
    }
}

void expect_size(size_t want, const char *what) {
    if (g_events.size() != want) {
        std::fprintf(stderr, "FAIL: %s (expected %zu events, got %zu)\n",
                     what, want, g_events.size());
        ++g_failures;
    }
}

void expect_event(size_t i, uint16_t type, uint16_t code, int32_t value,
                  const char *what) {
    if (i >= g_events.size()) {
        std::fprintf(stderr, "FAIL: %s (no event %zu)\n", what, i);
        ++g_failures;
        return;
    }
    const Event &e = g_events[i];
    expect(e.type == type && e.code == code && e.value == value, what);
}

} // namespace

int main() {
    // --- 1. extern constant sets (defined in uInputResource.cpp) ----------
    expect(DefaultEventTypes.count(EV_KEY) == 1, "DefaultEventTypes contains EV_KEY");
    expect(DefaultEventTypes.count(EV_REL) == 1, "DefaultEventTypes contains EV_REL");
    expect(DefaultEventTypes.count(EV_ABS) == 1, "DefaultEventTypes contains EV_ABS");
    expect(DefaultKeys.count(KEY_ENTER) == 1, "DefaultKeys contains KEY_ENTER");
    expect(DefaultKeys.size() > 100, "DefaultKeys is a large set");
    expect(DefaultRels.count(REL_X) == 1, "DefaultRels contains REL_X");
    expect(DefaultRels.count(REL_WHEEL) == 1, "DefaultRels contains REL_WHEEL");
    expect(DefaultAbss.count(ABS_MT_POSITION_X) == 1, "DefaultAbss contains ABS_MT_POSITION_X");

    // --- 2. setup classes --------------------------------------------------
    uInputDeviceInfo info("conan-test-device");
    expect(info.Vendor == 0x2333, "uInputDeviceInfo default vendor");
    expect(info.Product == 0x6666, "uInputDeviceInfo default product");
    expect(info.Name() == "conan-test-device", "uInputDeviceInfo Name() getter");
    info.Name("renamed-device");
    expect(info.Name() == "renamed-device", "uInputDeviceInfo Name() setter");
    info.BusType = BUS_VIRTUAL;
    expect(info.BusType == BUS_VIRTUAL, "uInputDeviceInfo BusType reference");

    uInputAbsSetup abs_x(ABS_X, 4095);
    expect(abs_x.Code == ABS_X, "uInputAbsSetup Code reference");
    expect(abs_x.Max == 4095, "uInputAbsSetup Max reference");

    uInputSetup setup(info, {EV_KEY, EV_REL}, {KEY_A, KEY_ENTER}, DefaultRels);
    expect(setup.Events.count(EV_KEY) == 1, "uInputSetup Events copied");
    expect(setup.Keys.count(KEY_A) == 1, "uInputSetup Keys copied");
    expect(setup.DeviceInfo.Name() == "renamed-device", "uInputSetup keeps DeviceInfo");

    // Default arguments (keys = DefaultKeys ...) apply to the parameterized
    // ctor; the defaulted default-ctor leaves the sets empty.
    uInputSetup defaults(uInputDeviceInfo("default-device"));
    expect(defaults.Keys.size() == DefaultKeys.size(), "uInputSetup default keys = DefaultKeys");
    uInputSetup empty;
    expect(empty.Keys.empty(), "uInputSetup default-constructed leaves Keys empty");

    // --- 3. emit pipeline in callback mode (no /dev/uinput needed) ---------
    uInput uinput;
    expect(uinput.FD == -1, "uInput default FD is -1");
    uinput.Init(record_event, nullptr);

    g_events.clear();
    uinput.SendKey(KEY_A, 1);
    expect_size(2, "SendKey emits key + SYN_REPORT");
    expect_event(0, EV_KEY, KEY_A, 1, "SendKey key-down event");
    expect_event(1, EV_SYN, SYN_REPORT, 0, "SendKey SYN_REPORT event");

    g_events.clear();
    uinput.SendKeyPress({KEY_LEFTCTRL, KEY_C});
    expect_size(8, "SendKeyPress(2 keys) emits down+SYN+up+SYN per key");
    expect_event(0, EV_KEY, KEY_LEFTCTRL, 1, "SendKeyPress key0 down");
    expect_event(1, EV_SYN, SYN_REPORT, 0, "SendKeyPress key0 SYN");
    expect_event(2, EV_KEY, KEY_LEFTCTRL, 0, "SendKeyPress key0 up");
    expect_event(4, EV_KEY, KEY_C, 1, "SendKeyPress key1 down");

    g_events.clear();
    uinput.RelativeMove(uInputCoordinate(5, -3));
    expect_size(3, "RelativeMove(5,-3) emits REL_X + REL_Y + SYN");
    expect_event(0, EV_REL, REL_X, 5, "RelativeMove REL_X");
    expect_event(1, EV_REL, REL_Y, -3, "RelativeMove REL_Y");
    expect_event(2, EV_SYN, SYN_REPORT, 0, "RelativeMove SYN");

    g_events.clear();
    uinput.RelativeMove(uInputCoordinate(0, 7));
    expect_size(2, "RelativeMove skips zero axes");
    expect_event(0, EV_REL, REL_Y, 7, "RelativeMove only nonzero axis");

    g_events.clear();
    uinput.RelativeWheel(-2);
    expect_size(2, "RelativeWheel emits REL_WHEEL + SYN");
    expect_event(0, EV_REL, REL_WHEEL, -2, "RelativeWheel value");

    g_events.clear();
    uinput.AbsolutePosition(uInputCoordinate(100, 200), -1);
    expect_size(3, "AbsolutePosition(slot=-1) emits ABS_X + ABS_Y + SYN");
    expect_event(0, EV_ABS, ABS_X, 100, "AbsolutePosition ABS_X");
    expect_event(1, EV_ABS, ABS_Y, 200, "AbsolutePosition ABS_Y");

    if (g_failures == 0) {
        std::printf("test_uinputplus: all assertions passed\n");
        return 0;
    }
    std::fprintf(stderr, "test_uinputplus: %d assertion(s) failed\n", g_failures);
    return 1;
}
