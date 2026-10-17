#include <mapbox/pixelmatch.hpp>

#include <vector>
#include <cstdint>
#include <iostream>

// Consumer test: uses only the installed public header + public API
// mapbox::pixelmatch(). Builds two 1x1 RGBA images that differ in one
// pixel and asserts the returned mismatch count equals the expected 1,
// plus a non-null diff buffer output.
int main() {
    const std::size_t width = 1;
    const std::size_t height = 1;
    const std::size_t size = width * height * 4;

    // Image A: opaque black pixel
    std::vector<uint8_t> img1 = {0, 0, 0, 255};
    // Image B: opaque white pixel
    std::vector<uint8_t> img2 = {255, 255, 255, 255};
    std::vector<uint8_t> diff(size, 0);

    uint64_t mismatch = mapbox::pixelmatch(
        img1.data(), img2.data(), width, height, diff.data(), 0.1, false);

    if (mismatch != 1) {
        std::cerr << "FAIL: expected 1 mismatched pixel, got " << mismatch << std::endl;
        return 1;
    }
    // Identical images must yield zero mismatches and an unchanged diff.
    std::vector<uint8_t> same = {7, 7, 7, 255};
    uint64_t mismatch2 = mapbox::pixelmatch(
        same.data(), same.data(), width, height, diff.data(), 0.1, false);
    if (mismatch2 != 0) {
        std::cerr << "FAIL: identical images must have 0 mismatches, got "
                  << mismatch2 << std::endl;
        return 1;
    }
    std::cout << "pixelmatch-cpp consumer test OK: mismatch=1, identical=0" << std::endl;
    return 0;
}
