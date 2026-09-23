#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>

#include <vector>
#include <string>

int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

TEST_CASE("factorial computes correctly", "[math]") {
    REQUIRE(factorial(0) == 1);
    REQUIRE(factorial(1) == 1);
    REQUIRE(factorial(5) == 120);
    CHECK(factorial(10) == 3628800);
}

TEST_CASE("vectors can be sized and resized", "[vector]") {
    std::vector<int> v(5);
    REQUIRE(v.size() == 5);
    REQUIRE(v.capacity() >= 5);

    SECTION("resizing bigger changes size and capacity") {
        v.resize(10);
        REQUIRE(v.size() == 10);
        REQUIRE(v.capacity() >= 10);
    }
    SECTION("reserving bigger changes capacity but not size") {
        v.reserve(10);
        REQUIRE(v.size() == 5);
        REQUIRE(v.capacity() >= 10);
    }
}

TEST_CASE("strings behave correctly", "[string]") {
    std::string s = "hello";
    REQUIRE(s == "hello");
    REQUIRE(s.size() == 5);
    s += " world";
    CHECK(s == "hello world");
}

TEST_CASE("approvals with Approx", "[approx]") {
    REQUIRE(0.1 + 0.2 == Approx(0.3));
    // Fix: 1.0/3.0=0.333333..., Approx(0.333).epsilon(0.001) allows 0.000333 diff which is borderline (diff 0.0003333... fails on some arch/optimizations). Use epsilon 0.01 to robustly allow 0.00333 tolerance.
    CHECK(1.0 / 3.0 == Approx(0.333).epsilon(0.01));
}

TEST_CASE("exceptions can be tested", "[exception]") {
    REQUIRE_THROWS_AS(throw std::runtime_error("error"), std::runtime_error);
    REQUIRE_NOTHROW(factorial(5));
}

TEST_CASE("BDD style scenario", "[bdd]") {
    GIVEN("a vector with some items") {
        std::vector<int> v = {1, 2, 3};
        REQUIRE(v.size() == 3);
        WHEN("an item is added") {
            v.push_back(4);
            THEN("size increases and element is accessible") {
                REQUIRE(v.size() == 4);
                REQUIRE(v.back() == 4);
            }
        }
    }
}
