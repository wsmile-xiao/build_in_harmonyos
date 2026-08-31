// test_package for ctre 3.10.0 — compile-time regex runtime matching smoke test
#include <ctre.hpp>
#include <string>
#include <iostream>

int main() {
    // Compile-time pattern literal (CTRE C++17 feature)
    // NOTE: template non-type argument requires a static constexpr fixed_string
    //       (a non-static constexpr local has no constant address in C++17).
    static constexpr auto pattern = ctll::fixed_string{"h.*o"};
    static_assert(ctre::match<pattern>("hello"));
    static_assert(ctre::match<pattern>("hrkwo"));

    // Runtime string matching via search
    static constexpr auto search_pat = ctll::fixed_string{"h.*o"};
    std::string s = "say hello world";
    auto m = ctre::search<search_pat>(s);
    if (!m) {
        std::cerr << "FAIL: expected match in '" << s << "'\n";
        return 1;
    }
    std::cout << "matched: '" << m.to_view() << "'\n";

    // Number extraction
    static constexpr auto num = ctll::fixed_string{"[0-9]+"};
    auto n = ctre::match<num>("2026");
    if (!n) {
        std::cerr << "FAIL: expected numeric match\n";
        return 1;
    }
    std::cout << "number: '" << n.to_view() << "'\n";

    std::cout << "ctre test_package OK\n";
    return 0;
}