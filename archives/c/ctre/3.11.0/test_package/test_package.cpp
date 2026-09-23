// test_package for ctre 3.11.0 — compile-time regex consumer checks
// 4 real API checks: match (static_assert) + search + numeric + named captures.
// The binary counts its own results and prints HMBS_TEST_PACKAGE_RESULT.
#include <ctre.hpp>
#include <string>
#include <iostream>

int main() {
    int discovered = 4;
    int passed = 0;

    // Check 1: compile-time match (static_assert) + runtime confirmation
    static constexpr auto pattern = ctll::fixed_string{"h.*o"};
    static_assert(ctre::match<pattern>("hello"));
    static_assert(ctre::match<pattern>("hrkwo"));
    std::cout << "Test 1: match<h.*o> static_assert OK" << std::endl;
    passed++;

    // Check 2: runtime search for substring
    static constexpr auto search_pat = ctll::fixed_string{"h.*o"};
    std::string s = "say hello world";
    auto m = ctre::search<search_pat>(s);
    if (!m) {
        std::cerr << "Test 2: FAIL: expected match in '" << s << "'" << std::endl;
    } else {
        std::cout << "Test 2: search matched: '" << m.to_view() << "'" << std::endl;
        passed++;
    }

    // Check 3: numeric extraction
    static constexpr auto num = ctll::fixed_string{"[0-9]+"};
    auto n = ctre::match<num>("2026");
    if (!n) {
        std::cerr << "Test 3: FAIL: expected numeric match" << std::endl;
    } else {
        std::cout << "Test 3: number: '" << n.to_view() << "'" << std::endl;
        passed++;
    }

    // Check 4: named capture groups (date split)
    // NOTE(C++17): return_type.hpp declares get() as template<const auto &Name>,
    // so d.get<"year">() (string literal NTTP) is rejected by clang-15 in C++17
    // mode. The pattern still uses (?<year>...)/(?<month>...) named groups;
    // verify them positionally (group 1=year, 2=month), which is portable.
    static constexpr auto date = ctll::fixed_string{"(?<year>[0-9]{4})-(?<month>[0-9]{2})"};
    auto d = ctre::match<date>("2026-09");
    if (!d) {
        std::cerr << "Test 4: FAIL: expected date match" << std::endl;
    } else if (d.get<1>().to_view() != "2026" || d.get<2>().to_view() != "09") {
        std::cerr << "Test 4: FAIL: named captures mismatch" << std::endl;
    } else {
        std::cout << "Test 4: year=" << d.get<1>().to_view()
                  << " month=" << d.get<2>().to_view() << std::endl;
        passed++;
    }

    bool ok = (passed == discovered);
    std::cout << "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":"
              << (ok ? "true" : "false")
              << ",\"command\":\"./test_package\",\"discovered\":" << discovered
              << ",\"passedCount\":" << passed << "}" << std::endl;
    std::cout << "Consumer test: " << passed << "/" << discovered << " passed" << std::endl;
    return ok ? 0 : 1;
}
