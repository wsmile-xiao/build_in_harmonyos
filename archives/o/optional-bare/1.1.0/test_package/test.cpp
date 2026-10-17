// Consumer test for optional-bare 1.1.0 (nonstd::optional)
// Compiled at C++14 so the nonstd implementation is exercised
// (at C++17 the header delegates to std::optional).
#include <nonstd/optional.hpp>
#include <cstdio>
#include <string>

using nonstd::optional;
using nonstd::nullopt;

static int g_checks = 0;
static int g_failed = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; std::printf("FAIL: %s\n", #cond); } } while(0)

optional<int> to_int(const std::string& text) {
    if (text.empty()) return nullopt;
    return nonstd::make_optional(std::stoi(text));
}

int main() {
    optional<int> a(42);
    CHECK(a.has_value());
    CHECK(bool(a));
    CHECK(a.value() == 42);
    CHECK(*a == 42);

    optional<int> b = nullopt;
    CHECK(!b.has_value());
    CHECK(b.value_or(7) == 7);

    optional<std::string> s = nonstd::make_optional(std::string("ohos"));
    CHECK(s.has_value());
    CHECK(s->size() == 4);
    s.reset();
    CHECK(!s.has_value());

    optional<int> c = to_int("21");
    CHECK(c.has_value());
    CHECK(c.value() == 21);

    optional<int> d = to_int("");
    CHECK(!d.has_value());
    CHECK(d == nullopt);

    optional<int> e1 = 1;
    optional<int> e2 = 2;
    CHECK(e1 < e2);
    CHECK(e1 != e2);
    e1.swap(e2);
    CHECK(e1.value() == 2 && e2.value() == 1);

    std::printf("optional-bare test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
