// Conan test_package consumer for memsafe 0.4.0.
// Uses ONLY the installed public header memsafe.h and its public API
// (memsafe::Shared / memsafe::Weak / memsafe::Locker) to verify a third-party
// consumer can compile, link, run and observe real results on OHOS.
#include <memsafe.h>

#include <cstdio>
#include <cstdlib>

int main() {
    // 1. Synchronized shared value via the public wrapper API.
    memsafe::Shared<int> value(21);
    *value.lock() = 42;                      // public lock() -> Locker deref
    if (*value.lock() != 42) {
        std::printf("FAIL: shared value write/read mismatch\n");
        return 1;
    }

    // 2. Weak reference path (public weak() + lock()).
    memsafe::Weak<memsafe::Shared<int>> weak_ref = value.weak();
    if (*weak_ref.lock() != 42) {
        std::printf("FAIL: weak ref read mismatch\n");
        return 1;
    }

    // 3. Explicit set() observable result.
    value.set(7);
    if (*value.lock() != 7) {
        std::printf("FAIL: set() mismatch\n");
        return 1;
    }

    std::printf("test_memsafe: OK (shared=7, weak=7)\n");
    return 0;
}
