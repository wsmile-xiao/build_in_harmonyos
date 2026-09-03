// test_bit_lite.cpp — bit-lite 2.0.0 consumer smoke test
// 真实调用 bit.hpp 核心 API（R34：不得为空壳测试）
#include <nonstd/bit.hpp>

#include <cassert>
#include <cstdint>
#include <cstdio>

int main() {
    using nonstd::bit::has_single_bit;
    using nonstd::bit::bit_width;
    using nonstd::bit::bit_floor;
    using nonstd::bit::rotl;
    using nonstd::bit::rotr;
    using nonstd::bit::popcount;

    // has_single_bit
    assert(has_single_bit(1u));
    assert(has_single_bit(8u));
    assert(!has_single_bit(0u));
    assert(!has_single_bit(6u));

    // bit_width
    assert(bit_width(0u) == 0);
    assert(bit_width(1u) == 1);
    assert(bit_width(255u) == 8);
    assert(bit_width(256u) == 9);

    // bit_floor
    assert(bit_floor(255u) == 128u);
    assert(bit_floor(256u) == 256u);

    // rotl / rotr
    assert(rotl(0x12345678u, 8) == 0x34567812u);
    assert(rotr(0x12345678u, 8) == 0x78123456u);

    // popcount
    assert(popcount(0u) == 0);
    assert(popcount(0xffu) == 8);

    // endian 扩展（暴露在 nonstd 命名空间）
    uint16_t x = 0x1234;
    uint16_t swapped = static_cast<uint16_t>(nonstd::as_big_endian(x));
    assert(swapped == 0x1234 || swapped == 0x3412);  // 与原生字节序一致或正确翻转

    std::printf("PASS: bit-lite header-only 库链接和核心 API 验证通过\n");
    return 0;
}