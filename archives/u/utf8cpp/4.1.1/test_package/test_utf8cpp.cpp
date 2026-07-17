// test_utf8cpp.cpp — L1 smoke test for utf8cpp 4.1.1 header-only library
// 验证 utf8cpp 头文件可正常包含、UTF-8 编解码、长度计算、迭代器功能正常
#include <utf8cpp/utf8.h>
#include <iostream>
#include <string>
#include <vector>

int main() {
    // 测试 1: UTF-8 字符串长度计算（字符数 vs 字节数）
    // "你好" = 2 个字符，6 个 UTF-8 字节
    const std::string u8str = u8"你好";
    auto char_count = utf8::distance(u8str.begin(), u8str.end());
    if (char_count != 2) {
        std::cerr << "FAIL: 字符数应为 2，实际为 " << char_count << std::endl;
        return 1;
    }
    if (u8str.size() != 6) {
        std::cerr << "FAIL: 字节数应为 6，实际为 " << u8str.size() << std::endl;
        return 1;
    }

    // 测试 2: UTF-8 到 UTF-32 转换
    std::vector<uint32_t> u32str;
    utf8::utf8to32(u8str.begin(), u8str.end(), std::back_inserter(u32str));
    if (u32str.size() != 2) {
        std::cerr << "FAIL: UTF-32 转换后长度应为 2" << std::endl;
        return 1;
    }
    // "你" = U+4F60, "好" = U+597D
    if (u32str[0] != 0x4F60 || u32str[1] != 0x597D) {
        std::cerr << "FAIL: UTF-32 码点不匹配" << std::endl;
        return 1;
    }

    // 测试 3: UTF-32 到 UTF-8 转换（往返）
    std::string u8roundtrip;
    utf8::utf32to8(u32str.begin(), u32str.end(), std::back_inserter(u8roundtrip));
    if (u8roundtrip != u8str) {
        std::cerr << "FAIL: UTF-8 往返转换不匹配" << std::endl;
        return 1;
    }

    // 测试 4: UTF-8 字符串有效性验证
    bool is_valid = utf8::is_valid(u8str.begin(), u8str.end());
    if (!is_valid) {
        std::cerr << "FAIL: 有效 UTF-8 字符串未被识别" << std::endl;
        return 1;
    }

    // 测试 5: UTF-8 迭代器遍历
    unsigned int iter_count = 0;
    for (auto it = u8str.begin(); it != u8str.end(); utf8::next(it, u8str.end())) {
        iter_count++;
    }
    if (iter_count != 2) {
        std::cerr << "FAIL: 迭代器遍历字符数应为 2" << std::endl;
        return 1;
    }

    std::cout << "PASS: utf8cpp header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
