#include <re2/re2.h>

#include <cassert>
#include <iostream>
#include <string>

int main() {
    // Test 1: Full match with capture groups (mirrors upstream
    // re2/testing/re2_test.cc FullMatch cases)
    re2::RE2 re("h(e)(l)(l)(o)");
    assert(re.ok());
    std::string a, b, c, d;
    assert(re2::RE2::FullMatch("hello", re, &a, &b, &c, &d));
    assert(a == "e");
    assert(b == "l");
    assert(c == "l");
    assert(d == "o");

    // Test 2: Partial match
    assert(re2::RE2::PartialMatch("say hello world", "hello"));
    assert(!re2::RE2::PartialMatch("bye world", "hello"));

    // Test 3: Replace (in-place) — digits regex
    std::string str = "foo123bar";
    assert(re2::RE2::Replace(&str, "\\d+", "#"));
    assert(str == "foo#bar");

    // Test 4: Global replace
    std::string g = "a1b22c333";
    assert(re2::RE2::GlobalReplace(&g, "\\d+", "-"));
    assert(g == "a-b-c-");

    // Test 5: Integer extraction
    int i = 0;
    assert(re2::RE2::FullMatch("12345", "(\\d+)", &i));
    assert(i == 12345);

    // Test 6: Anchored full match must not accept partial input
    assert(!re2::RE2::FullMatch("hello world", "hello"));

    // Test 7 (HarmonyOS-specific): the OHOS target must expose the platform
    // macro this adaptation relies on; re2 must stay little-endian-clean on
    // the aarch64 OHOS device for its bitmap-based bitstate engine.
#if defined(__OHOS__)
    std::cout << "OHOS platform confirmed" << std::endl;
#else
    std::cout << "non-OHOS host (build-only check)" << std::endl;
#endif
    const std::uint16_t probe = 0x0001;
    assert(*reinterpret_cast<const std::uint8_t*>(&probe) == 1);

    std::cout << "All re2 tests passed!" << std::endl;
    return 0;
}
