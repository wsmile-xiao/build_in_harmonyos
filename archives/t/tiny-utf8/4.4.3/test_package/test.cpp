// test_package consumer test for tiny-utf8 4.4.3
// Exercises the real public API of the tiny_utf8::string class:
// construction from UTF-8 literal, length()/size(), iteration over code
// points, substr/find, operator[], and comparison operators.
// NOTE: uses explicit checks (not assert()) so assertions remain effective
// under Release/NDEBUG builds (OHOS aarch64 default).
#include <cstdio>
#include <string>

#include <tinyutf8/tinyutf8.h>

#define TINYUTF8_CHECK(cond)                                                     \
    do {                                                                         \
        if (!(cond)) {                                                           \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return 1;                                                            \
        }                                                                        \
    } while (0)

int main(void) {
    // Multi-byte UTF-8 text: "Hello, 世界!" — 10 code points, 14 UTF-8 bytes
    // (5 ASCII + ',' + ' ' + 2x3-byte CJK + '!').
    tiny_utf8::string s(u8"Hello, 世界!");

    // length() = code points (UTF-8 aware), size() = bytes.
    TINYUTF8_CHECK(s.length() == 10);
    TINYUTF8_CHECK(s.size() == 14);

    // Range iteration yields code points in order.
    std::u32string cp;
    for (char32_t c : s) {
        cp.push_back(c);
    }
    std::u32string expected = U"Hello, 世界!";
    TINYUTF8_CHECK(cp == expected);

    // Substring at code-point granularity.
    tiny_utf8::string sub = s.substr(7, 2);
    TINYUTF8_CHECK(sub == u8"世界");
    TINYUTF8_CHECK(sub.length() == 2);

    // Find returns code-point index of the pattern.
    TINYUTF8_CHECK(s.find(u8"世界") == 7);
    TINYUTF8_CHECK(s.find(u8"世界", 8) == tiny_utf8::string::npos);

    // Comparison with string literals.
    TINYUTF8_CHECK(s == u8"Hello, 世界!");
    TINYUTF8_CHECK(s != u8"Hello!");

    // operator[] yields a code point (char32_t) at code-point index.
    TINYUTF8_CHECK(s[7] == U'世');
    TINYUTF8_CHECK(s[0] == U'H');

    // round-trip: build from std::u32string via iterators.
    tiny_utf8::string rebuilt(expected.begin(), expected.end());
    TINYUTF8_CHECK(rebuilt == s);

    std::printf("test_tiny-utf8: consumer API check OK (%zu bytes, %zu code points)\n",
                static_cast<size_t>(s.size()), static_cast<size_t>(s.length()));
    return 0;
}