// Consumer test for tl-expected 1.3.1
#include <tl/expected.hpp>
#include <cstdio>
#include <string>

static int g_checks = 0;
static int g_failed = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; std::printf("FAIL: %s\n", #cond); } } while(0)

tl::expected<int, std::string> divide(int a, int b) {
    if (b == 0) return tl::make_unexpected(std::string("division by zero"));
    return a / b;
}

int main() {
    auto r1 = divide(10, 2);
    CHECK(r1.has_value());
    CHECK(r1.value() == 5);

    auto r2 = divide(10, 0);
    CHECK(!r2.has_value());
    CHECK(r2.error() == "division by zero");

    auto r3 = divide(20, 4).map([](int v) { return v * 2; });
    CHECK(r3.has_value());
    CHECK(r3.value() == 10);

    std::printf("tl-expected test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
