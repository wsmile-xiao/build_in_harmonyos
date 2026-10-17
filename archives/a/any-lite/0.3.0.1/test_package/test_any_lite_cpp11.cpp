// C++11 consumer test: forces the nonstd backport implementation because
// std::any is unavailable in C++11.
#include <nonstd/any.hpp>

#include <iostream>
#include <string>
#include <typeinfo>

int main() {
    nonstd::any value = 7;
    if (nonstd::any_cast<int>(value) != 7) {
        std::cerr << "FAIL: C++11 any_cast<int> should return 7" << std::endl;
        return 1;
    }

    if (nonstd::any_cast<int>(&value) == nullptr) {
        std::cerr << "FAIL: C++11 pointer any_cast should find int" << std::endl;
        return 1;
    }

    if (value.type() != typeid(int)) {
        std::cerr << "FAIL: C++11 any should report typeid(int)" << std::endl;
        return 1;
    }

    value = std::string("cpp11");
    if (nonstd::any_cast<std::string>(value) != "cpp11") {
        std::cerr << "FAIL: C++11 any_cast<string> should return cpp11" << std::endl;
        return 1;
    }

    nonstd::any empty;
    if (empty.has_value()) {
        std::cerr << "FAIL: C++11 default-constructed any should be empty" << std::endl;
        return 1;
    }

    try {
        (void)nonstd::any_cast<int>(value);
        std::cerr << "FAIL: C++11 bad any_cast should throw nonstd::bad_any_cast" << std::endl;
        return 1;
    } catch (nonstd::bad_any_cast const&) {
        // Expected.
    }

    std::cout << "PASS: any-lite C++11 nonstd backport consumer test" << std::endl;
    return 0;
}
