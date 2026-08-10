#include <re2/re2.h>
#include <cassert>
#include <iostream>

int main() {
    // Test 1: Basic full match with capture groups
    re2::RE2 re("h(e)(l)(l)(o)");
    std::string s = "hello";
    std::string a, b, c, d;
    assert(re2::RE2::FullMatch(s, re, &a, &b, &c, &d));
    assert(a == "e");
    assert(b == "l");
    assert(c == "l");
    assert(d == "o");

    // Test 2: Partial match
    assert(re2::RE2::PartialMatch("say hello world", "hello"));

    // Test 3: Replace (in-place)
    std::string str = "foo123bar";
    re2::RE2::Replace(&str, "\\d+", "#");
    assert(str == "foo#bar");

    std::cout << "All re2 tests passed!" << std::endl;
    return 0;
}
