#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>

TEST_CASE("Catch2 package provides a working test runner", "[package]")
{
    REQUIRE(2 + 2 == 4);
}

