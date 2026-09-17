// test_jpcre2.cpp — jpcre2 10.32.01 consumer test (C++).
// Exercises the real public API from <jpcre2.hpp> against the PCRE2 C
// library: bool match, global match count, numbered substrings, replace,
// JIT compile path, and a negative match. 7 explicit checks; any failure
// returns 1 so ctest/conan goes red.
#include <iostream>
#include <string>
#include "jpcre2.hpp"

typedef jpcre2::select<char> jp;

static int s_check = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        ++s_check;                                         \
        if (!(cond)) {                                     \
            std::cerr << "CHECK " << s_check               \
                      << " FAILED: " << msg << std::endl;  \
            return 1;                                      \
        }                                                  \
        std::cout << "CHECK " << s_check                   \
                  << " passed: " << msg << std::endl;      \
    } while (0)

int main() {
    // 1. Simple boolean match.
    CHECK(jp::Regex("(\\d+)").match("abc 123") == true,
          "bool match finds digits");

    // 2. Global match count with action modifier 'g'.
    size_t n = jp::Regex("(\\w+)", "m").match("aa 11 bb", "g");
    CHECK(n == 3, "global match count == 3");

    // 3. Numbered substrings / captured groups.
    jp::VecNum vec_num;
    jp::Regex re3("(\\w+)\\s*(\\d+)", "m");
    size_t c3 = jp::RegexMatch(&re3)
                    .setSubject("hello 42")
                    .setModifier("g")
                    .setNumberedSubstringVector(&vec_num)
                    .match();
    CHECK(c3 >= 1 && vec_num.size() >= 1 && vec_num[0].size() >= 3,
          "captured-group vector populated");
    CHECK(vec_num[0][1] == "hello" && vec_num[0][2] == "42",
          "captured groups hello/42");

    // 4. Regex replace.
    jp::Regex re4("\\d+");
    jp::RegexReplace rr4(&re4);
    std::string s4 = "a1b22";
    std::string out4 = rr4.setSubject(&s4)
                           .setReplaceWith("NUM")
                           .addModifier("g")
                           .replace();
    CHECK(out4 == "aNUMbNUM", "replace digits with NUM");

    // 5. JIT compile path (harmless if JIT unavailable, still matches).
    jp::Regex re5("(\\w+)\\s*(\\d+)", "mS");
    CHECK(re5.match("hello 42") == true, "JIT-compiled pattern matches");

    // 6. Negative match returns false.
    CHECK(jp::Regex("(\\d+)").match("no digits here") == false,
          "negative match returns false");

    std::cout << "test jpcre2 10.32.01: all " << s_check
              << " checks passed" << std::endl;
    return 0;
}
