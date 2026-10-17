// test_package/test_catch.cpp — consumer test for catch 1.12.2 (R34)
// Exercises the framework the way a downstream project does: CATCH_CONFIG_MAIN
// provides main(), TEST_CASE/SECTION/REQUIRE/REQUIRE_FALSE/Approx drive real
// assertions, and the Catch runner reports the summary.
#define CATCH_CONFIG_MAIN
#include <catch.hpp>

TEST_CASE("arithmetic and comparison macros", "[package][math]") {
    REQUIRE(2 + 2 == 4);
    REQUIRE_FALSE(1 == 2);

    SECTION("negation") {
        REQUIRE(-1 == 0 - 1);
    }
    SECTION("floating point tolerance via Approx") {
        REQUIRE(0.1 + 0.2 == Approx(0.3));
    }
}

TEST_CASE("string handling", "[package][strings]") {
    std::string s = "catch";
    REQUIRE(s.size() == 5u);
    REQUIRE(s.substr(0, 3) == "cat");

    SECTION("append") {
        s += " 1.12.2";
        REQUIRE(s == "catch 1.12.2");
    }
}
