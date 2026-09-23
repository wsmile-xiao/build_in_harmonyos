// test_optional_lite_ext.cpp — optional-lite 3.6.0 extension API consumer test
// (C++14 nonstd backport implementation mode)
// 3.6.0 upstream addition value_or_eval(): returns contained value when engaged,
// f() when empty
#include <nonstd/optional.hpp>
#include <iostream>
#include <string>

int main() {
#if optional_USES_STD_OPTIONAL
    std::cerr << "FAIL: C++14 build should use the nonstd backport implementation" << std::endl;
    return 1;
#endif

    // Test 1: value_or_eval on non-empty optional returns the contained value
    nonstd::optional<int> e(42);
    if (e.value_or_eval([]() { return 7; }) != 42) {
        std::cerr << "FAIL: value_or_eval on non-empty should return 42" << std::endl;
        return 1;
    }

    // Test 2: value_or_eval on empty optional returns f()
    nonstd::optional<int> d;
    if (d.value_or_eval([]() { return 7; }) != 7) {
        std::cerr << "FAIL: value_or_eval on empty should return 7" << std::endl;
        return 1;
    }

    // Test 3: rvalue optional value_or_eval (C++11 ref-qualified overload)
    if (nonstd::optional<std::string>("77").value_or_eval(
            []() { return std::string("7"); }) != "77") {
        std::cerr << "FAIL: rvalue value_or_eval should return contained 77" << std::endl;
        return 1;
    }

    std::cout << "PASS: optional-lite 3.6.0 value_or_eval extension API verified (C++14 nonstd mode)" << std::endl;
    return 0;
}
