// test_optional_lite.cpp — L1 smoke test for optional-lite 3.6.0 header-only library
// C++17 mode: header inclusion, optional core construct/access APIs
#include <nonstd/optional.hpp>
#include <iostream>
#include <string>

int main() {
    // Test 1: empty optional
    nonstd::optional<int> empty;
    if (empty.has_value()) {
        std::cerr << "FAIL: empty optional should not have value" << std::endl;
        return 1;
    }

    // Test 2: optional with value
    nonstd::optional<int> opt = 42;
    if (!opt.has_value() || *opt != 42) {
        std::cerr << "FAIL: optional value should be 42" << std::endl;
        return 1;
    }

    // Test 3: value() access
    if (opt.value() != 42) {
        std::cerr << "FAIL: value() should return 42" << std::endl;
        return 1;
    }

    // Test 4: value_or default
    if (empty.value_or(99) != 99) {
        std::cerr << "FAIL: value_or should return 99" << std::endl;
        return 1;
    }

    // Test 5: make_optional
    auto opt2 = nonstd::make_optional(std::string("hello"));
    if (!opt2.has_value() || opt2->size() != 5) {
        std::cerr << "FAIL: make_optional string should have length 5" << std::endl;
        return 1;
    }

    // Test 6: reassignment
    opt = 100;
    if (*opt != 100) {
        std::cerr << "FAIL: reassigned value should be 100" << std::endl;
        return 1;
    }

    // Test 7: reset
    opt.reset();
    if (opt.has_value()) {
        std::cerr << "FAIL: reset should clear value" << std::endl;
        return 1;
    }

    // Test 8: emplace in-place construction
    opt.emplace(7);
    if (!opt.has_value() || *opt != 7) {
        std::cerr << "FAIL: emplace should construct value 7" << std::endl;
        return 1;
    }

    std::cout << "PASS: optional-lite 3.6.0 C++17 mode core API verified" << std::endl;
    return 0;
}
