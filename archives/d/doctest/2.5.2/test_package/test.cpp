#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"
#include <string>

TEST_CASE("doctest basic test") {
    int a = 1;
    int b = 1;
    CHECK(a == b);
}

TEST_CASE("doctest string test") {
    std::string s = "hello";
    CHECK(s.size() == 5);
}
