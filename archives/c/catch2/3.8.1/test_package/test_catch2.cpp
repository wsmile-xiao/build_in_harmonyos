#include <catch2/catch_test_macros.hpp>

TEST_CASE("Catch2 v3 package provides a working test runner", "[package]") {
    REQUIRE(2 + 2 == 4);
}
