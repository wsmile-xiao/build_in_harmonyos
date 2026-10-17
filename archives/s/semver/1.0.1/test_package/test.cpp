// Consumer test for semver 1.0.1 — exercises parse, compare, and to_string APIs.
#include <semver.hpp>
#include <cstdio>
#include <cstdint>
#include <string>

static int g_checks = 0;
static int g_failed = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; std::printf("FAIL: %s\n", #cond); } } while(0)

int main() {
    using version = semver::version<std::uint32_t, std::uint32_t, std::uint32_t>;

    // Parse a valid version string
    version v1{};
    auto r1 = semver::parse("1.2.3", v1);
    CHECK(r1.ec == std::errc{});
    CHECK(v1.major() == 1);
    CHECK(v1.minor() == 2);
    CHECK(v1.patch() == 3);

    // Compare versions
    version v2{};
    semver::parse("1.2.4", v2);
    CHECK(v1 < v2);
    CHECK(v2 > v1);
    CHECK(v1 != v2);

    // to_string round-trip
    CHECK(v1.to_string() == "1.2.3");

    // Pre-release
    version v3{};
    semver::parse("1.0.0-alpha+build.123", v3);
    CHECK(v3.major() == 1);
    CHECK(!v3.prerelease_tag().empty());

    std::printf("semver test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
