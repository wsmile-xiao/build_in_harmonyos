// Consumer test for optional 1.1.0 (tl::optional)
#include <tl/optional.hpp>
#include <cstdio>
#include <functional>
#include <string>

static int g_checks = 0;
static int g_failed = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; std::printf("FAIL: %s\n", #cond); } } while(0)

tl::optional<int> parse_int(const std::string& s) {
    if (s.empty()) return tl::nullopt;
    return std::stoi(s);
}

int main() {
    tl::optional<int> a = 42;
    CHECK(a.has_value());
    CHECK(a.value() == 42);
    CHECK(*a == 42);

    tl::optional<int> b;
    CHECK(!b.has_value());
    CHECK(b.value_or(7) == 7);

    auto c = tl::make_optional<std::string>("ohos");
    CHECK(c.has_value());
    CHECK(c->size() == 4);
    c.emplace("harmony");
    CHECK(*c == "harmony");

    auto d = parse_int("21").map([](int v) { return v * 2; });
    CHECK(d.has_value());
    CHECK(*d == 42);

    auto e = parse_int("").map([](int v) { return v * 2; });
    CHECK(!e.has_value());

    auto f = parse_int("10").and_then([](int v) -> tl::optional<int> {
        return v > 5 ? tl::optional<int>(v + 1) : tl::nullopt;
    });
    CHECK(f.has_value());
    CHECK(*f == 11);

    int storage = 5;
    tl::optional<int&> ref = storage;
    ref.map([](int& v) -> int& { v = 99; return v; });
    CHECK(storage == 99);

    tl::optional<int> g = 1, h = 2;
    CHECK(g < h);
    g.swap(h);
    CHECK(*g == 2 && *h == 1);

    auto hv = std::hash<tl::optional<int>>{}(a);
    (void)hv;
    CHECK(true);

    std::printf("optional test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
