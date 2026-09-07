// Consumer test for qaccessibilityclient/0.6.0 (L1 test_package).
//
// Mirrors the headless-safe assertions of upstream
// tests/auto/tst_accessibilityclient.cpp (tst_registry /
// tst_accessibleObject / tst_hashable slots): construct a Registry,
// toggle the NoEventListeners subscription and verify the recorded state,
// without requiring a live AT-SPI2 bus (the OHOS build host has no
// a11y session bus; upstream slots that browse a live tree are covered
// by the in-build ctest run recorded in the recipe).

#include <cstdio>

#include <QCoreApplication>

#include "qaccessibilityclient/registry.h"
#include "qaccessibilityclient/accessibleobject.h"

using namespace QAccessibleClient;

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    Registry registry;

    // upstream tst_registry(): subscription bookkeeping is pure state,
    // no D-Bus round-trip needed for NoEventListeners.
    if (registry.subscribedEventListeners() != Registry::NoEventListeners) {
        std::printf("FAIL: initial listener state is not NoEventListeners\n");
        return 1;
    }
    registry.subscribeEventListeners(Registry::NoEventListeners);
    if (registry.subscribedEventListeners() != Registry::NoEventListeners) {
        std::printf("FAIL: NoEventListeners subscription not recorded\n");
        return 1;
    }

    // upstream tst_accessibleObject(): default-constructed objects are invalid.
    AccessibleObject invalid;
    if (invalid.isValid()) {
        std::printf("FAIL: default AccessibleObject unexpectedly valid\n");
        return 1;
    }

    std::printf("test_qaccessibilityclient: QAccessibilityClient6 registry API OK "
                "(headless-safe subset)\n");
    return 0;
}
