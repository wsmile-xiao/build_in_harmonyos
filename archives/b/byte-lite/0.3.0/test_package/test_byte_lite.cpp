// test_byte_lite.cpp — L1 smoke test for byte-lite 0.3.0 header-only library
// 验证 nonstd/byte.hpp 头文件可正常包含、byte 构造与 to_integer/byte_cast 访问
#include <nonstd/byte.hpp>
#include <iostream>

int main() {
    // 测试 1: 默认构造 + to_integer 访问
    nonstd::byte b{0x42};
    if (nonstd::to_integer<int>(b) != 0x42) {
        std::cerr << "FAIL: to_integer(byte{0x42}) should return 0x42" << std::endl;
        return 1;
    }

    // 测试 2: 位运算（byte_lite 支持 & | ^ ~ 及位移）
    nonstd::byte low{0x0F};
    nonstd::byte high{0xF0};
    nonstd::byte combined = low | high;
    if (nonstd::to_integer<int>(combined) != 0xFF) {
        std::cerr << "FAIL: (low | high) should equal 0xFF" << std::endl;
        return 1;
    }
    nonstd::byte masked = combined & low;
    if (nonstd::to_integer<int>(masked) != 0x0F) {
        std::cerr << "FAIL: (combined & low) should equal 0x0F" << std::endl;
        return 1;
    }

    // 测试 3: 比较
    nonstd::byte b1{1};
    nonstd::byte b2{1};
    if (b1 != b2) {
        std::cerr << "FAIL: byte{1} should equal byte{1}" << std::endl;
        return 1;
    }

    std::cout << "PASS: byte-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
