#include <c4/version.hpp>
#include <c4/substr.hpp>
#include <iostream>

int main() {
    // Test version macro
    std::cout << "c4core version: " << C4CORE_VERSION << std::endl;

    // Test substr functionality
    const char text[] = "Hello c4core on HarmonyOS!";
    c4::csubstr s = c4::to_csubstr(text);
    std::cout << "substr content: " << s.str << std::endl;
    std::cout << "substr length: " << s.len << std::endl;

    if (s.len == sizeof(text) - 1) {
        std::cout << "All c4core tests passed!" << std::endl;
        return 0;
    } else {
        std::cerr << "Test failed: expected length 26, got " << s.len << std::endl;
        return 1;
    }
}
