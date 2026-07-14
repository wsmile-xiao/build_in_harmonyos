// test_charls.cpp — L1 smoke test for charls JPEG-LS library
// 验证 charls 库可用: 编码 -> 解码 -> 数据一致
#include <charls/charls_jpegls_encoder.h>
#include <charls/charls_jpegls_decoder.h>
#include <iostream>
#include <vector>
#include <cstring>

int main() {
    // 构造一个 8x8 灰度图像 (16-bit)
    const int width = 8;
    const int height = 8;
    const int bitsPerSample = 16;
    const int components = 1;
    std::vector<uint8_t> input(width * height * 2);
    for (int i = 0; i < width * height; i++) {
        uint16_t v = static_cast<uint16_t>(i * 100);
        input[i * 2] = static_cast<uint8_t>(v & 0xFF);
        input[i * 2 + 1] = static_cast<uint8_t>((v >> 8) & 0xFF);
    }

    // Test 1: 编码
    charls::jpegls_encoder encoder;
    charls::frame_info frame{width, height, bitsPerSample, components};
    encoder.frame_info(frame);
    encoder.interleave_mode(charls::interleave_mode::none);
    std::vector<uint8_t> encoded(encoder.estimated_destination_size());
    encoder.destination(encoded);
    size_t encoded_size = encoder.encode(input);
    encoded.resize(encoded_size);
    std::cout << "编码成功, 压缩后大小: " << encoded_size << " 字节" << std::endl;

    // Test 2: 验证编码后有数据
    if (encoded_size == 0) {
        std::cerr << "FAIL: 编码后数据为空" << std::endl;
        return 1;
    }

    // Test 3: 解码
    charls::jpegls_decoder decoder;
    decoder.source(encoded.data(), encoded.size());
    decoder.read_header();
    auto info = decoder.frame_info();
    std::vector<uint8_t> decoded(info.width * info.height * info.component_count * 2);
    decoder.decode(decoded);
    std::cout << "解码成功, 尺寸: " << info.width << "x" << info.height
              << ", 分量数: " << static_cast<int>(info.component_count) << std::endl;

    // Test 4: 验证解码数据与原始数据一致 (无损)
    if (decoded.size() != input.size()) {
        std::cerr << "FAIL: 解码数据大小 " << decoded.size()
                  << " 与原始 " << input.size() << " 不一致" << std::endl;
        return 1;
    }
    if (std::memcmp(decoded.data(), input.data(), input.size()) != 0) {
        std::cerr << "FAIL: 解码数据与原始数据不一致 (非无损)" << std::endl;
        return 1;
    }

    std::cout << "PASS: charls JPEG-LS 无损编解码验证通过" << std::endl;
    return 0;
}
