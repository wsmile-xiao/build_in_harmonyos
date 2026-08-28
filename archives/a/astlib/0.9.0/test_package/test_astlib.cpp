// test_astlib.cpp — Substantive test that calls astlib API (R34)
// Initializes codecs and verifies that built-in Asterix specifications are loaded.

#include <astlib/CodecRegister.h>
#include <astlib/Astlib.h>

#include <iostream>
#include <cstdlib>

int main() {
    // Initialize all built-in Asterix codec descriptions
    astlib::CodecRegister register_;
    register_.initializeCodecs();

    // Enumerate all registered codecs — should contain multiple categories
    auto codecs = register_.enumerateAllCodecs();

    if (codecs.empty()) {
        std::cerr << "FAIL: No codecs registered after initializeCodecs()" << std::endl;
        return 1;
    }

    std::cout << "PASS: " << codecs.size() << " codec(s) registered" << std::endl;

    // Verify we can look up a known category (cat001 = 1)
    auto codec = register_.getLatestCodecForCategory(1);
    if (!codec) {
        std::cerr << "FAIL: Could not get codec for category 1 (cat001)" << std::endl;
        return 1;
    }

    std::cout << "PASS: Category 1 codec found" << std::endl;
    return 0;
}
