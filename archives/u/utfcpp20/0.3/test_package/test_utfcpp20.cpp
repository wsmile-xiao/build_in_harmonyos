#include <utfcpp20.hpp>

#include <cstdio>
#include <string>
#include <string_view>

namespace {

int failures = 0;

void check(bool cond, const char* what, int line) {
    if (!cond) {
        std::fprintf(stderr, "FAIL: %s (line %d)\n", what, line);
        ++failures;
    }
}

}  // namespace

#define CHECK(cond) check((cond), #cond, __LINE__)

int main() {
    // 1) append_to_utf8: 1/2/3/4 字节序列各一种
    std::u8string s;
    utfcpp::append_to_utf8(s, U'a');
    utfcpp::append_to_utf8(s, U'\u043B');
    utfcpp::append_to_utf8(s, U'\u4F60');
    utfcpp::append_to_utf8(s, U'\U0001F600');
    CHECK(s.size() == 10);
    CHECK(s == u8"a\u043B\u4F60\U0001F600");

    // 2) append_to_utf16 与 utf8_to_16 一致性（emoji 为代理对，长度 5）
    std::u16string expect16;
    utfcpp::append_to_utf16(expect16, U'a');
    utfcpp::append_to_utf16(expect16, U'\u043B');
    utfcpp::append_to_utf16(expect16, U'\u4F60');
    utfcpp::append_to_utf16(expect16, U'\U0001F600');
    CHECK(expect16.size() == 5);
    CHECK(utfcpp::utf8_to_16(s) == expect16);
    CHECK(utfcpp::utf8_to_16(s).size() == 5);

    // 3) utf16_to_8 往返
    CHECK(utfcpp::utf16_to_8(expect16) == s);

    // 4) 无效 UTF-8 输入必须抛 utfcpp::exception（基准异常类捕获派生类）
    const char8_t invalid[] = {0x61, 0xFF, 0x62};
    const std::u8string_view bad_view(invalid, 3);
    bool threw = false;
    try {
        (void)utfcpp::utf8_to_16(bad_view);
    } catch (const utfcpp::exception&) {
        threw = true;
    }
    CHECK(threw);

    // 5) u8_iterator 解码往返
    std::u8string decoded;
    for (auto it = utfcpp::u8_iterator::begin(s); it != utfcpp::u8_iterator::end(s); ++it) {
        utfcpp::append_to_utf8(decoded, *it);
    }
    CHECK(decoded == s);

    // 6) 纯 ASCII 往返
    const std::u8string ascii = u8"abc";
    CHECK(utfcpp::utf16_to_8(utfcpp::utf8_to_16(ascii)) == ascii);

    if (failures != 0) {
        std::fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    std::printf(
        "utfcpp20 consumer test PASSED: append_to_utf8/append_to_utf16, "
        "utf8_to_16/utf16_to_8 round-trips, invalid-input rejection, "
        "u8_iterator decode (9 checks)\n");
    return 0;
}
