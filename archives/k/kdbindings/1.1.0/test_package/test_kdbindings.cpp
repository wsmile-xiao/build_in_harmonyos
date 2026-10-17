// test_package consumer test — kdbindings 1.1.0
// Actually exercises the KDBindings public API: Property set/get, reactive
// binding (makeBoundProperty) and Signal connect/emit/disconnect, proving the
// installed headers and CMake package config work for consumers.
#include <kdbindings/binding.h>
#include <kdbindings/property.h>
#include <kdbindings/signal.h>

#include <cstdio>

int main()
{
    // Property API: set/get and assignment
    KDBindings::Property<int> prop{42};
    if (prop.get() != 42) {
        std::printf("FAIL: initial value = %d, expected 42\n", prop.get());
        return 1;
    }
    prop.set(7);
    if (prop.get() != 7) {
        std::printf("FAIL: after set value = %d, expected 7\n", prop.get());
        return 1;
    }
    prop = 9;
    if (prop.get() != 9) {
        std::printf("FAIL: after assign value = %d, expected 9\n", prop.get());
        return 1;
    }

    // Reactive binding: bound property recomputes when inputs change
    KDBindings::Property<int> width{2};
    KDBindings::Property<int> height{3};
    const auto area = KDBindings::makeBoundProperty(width * height);
    if (area.get() != 6) {
        std::printf("FAIL: bound area = %d, expected 6\n", area.get());
        return 1;
    }
    width = 5;
    if (area.get() != 15) {
        std::printf("FAIL: re-bound area = %d, expected 15\n", area.get());
        return 1;
    }

    // Signal API: connect, emit, observe
    KDBindings::Signal<int> signal;
    int received = -1;
    auto connection = signal.connect([&received](int v) { received = v; });
    signal.emit(123);
    if (received != 123) {
        std::printf("FAIL: signal delivered %d, expected 123\n", received);
        return 1;
    }
    connection.disconnect();

    std::printf("test kdbindings 1.1.0: OK (prop=%d, area=%d, signal=%d)\n", prop.get(), area.get(), received);
    return 0;
}
