// test_package/test_lexy.cpp — R34: substantive test that uses lexy API.
// Builds a small DSL grammar (a signed integer rule) and runs lexy::parse
// against several inputs, asserting the parsed values. This exercises the
// actual lexy parser combinator machinery, not a placeholder string print.
#include <lexy/action/parse.hpp>
#include <lexy/callback.hpp>
#include <lexy/dsl.hpp>
#include <lexy/input/string_input.hpp>

#include <cassert>
#include <iostream>
#include <string>

namespace dsl = lexy::dsl;

// A simple grammar production: a signed integer.
struct integer {
    // dsl::sign matches an optional '+'/'-' and produces lexy::plus_sign /
    // lexy::minus_sign; dsl::integer matches the digits. `+` sequences both.
    // lexy::as_integer<int> consumes (sign, value) and returns the signed int.
    // (Same pattern as upstream examples/json.cpp exponent rule.)
    static constexpr auto rule = dsl::sign + dsl::integer<int>;
    static constexpr auto value = lexy::as_integer<int>;
};

template <typename Production, typename Input>
bool parse_ok(const Input& input, int expected) {
    auto result = lexy::parse<Production>(input, lexy::noop);
    if (!result.has_value()) {
        std::cerr << "FAIL: parse error on " << expected << "\n";
        return false;
    }
    if (result.value() != expected) {
        std::cerr << "FAIL: expected " << expected << ", got " << result.value() << "\n";
        return false;
    }
    return true;
}

int main() {
    bool ok = true;

    ok = parse_ok<integer>(lexy::zstring_input("42"), 42) && ok;
    ok = parse_ok<integer>(lexy::zstring_input("-17"), -17) && ok;
    ok = parse_ok<integer>(lexy::zstring_input("+123"), 123) && ok;
    ok = parse_ok<integer>(lexy::zstring_input("0"), 0) && ok;

    // A failing parse must be reported as failure (not crash, not success).
    {
        auto result = lexy::parse<integer>(lexy::zstring_input("abc"), lexy::noop);
        if (result.has_value()) {
            std::cerr << "FAIL: expected parse error on non-numeric input\n";
            ok = false;
        }
    }

    if (ok) {
        std::cout << "PASS: lexy parse tests (integers + rejection)\n";
        return 0;
    }
    return 1;
}
