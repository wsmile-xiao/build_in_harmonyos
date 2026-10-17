// test_optional.cpp — tl-optional 1.1.0 消费者测试
// 真实调用 tl::optional 核心 API 与扩展 API，编译并运行断言。
#include <tl/optional.hpp>
#include <cstdio>
#include <string>
#include <cassert>

static int g_checks = 0;
#define CHECK(expr) do { assert(expr); ++g_checks; } while (0)

int main() {
    // 核心构造 / 判空 / 取值
    tl::optional<int> a;
    CHECK(!a.has_value());
    tl::optional<int> b(42);
    CHECK(b.has_value());
    CHECK(b.value() == 42);
    CHECK(b.value_or(0) == 42);
    CHECK(a == tl::nullopt);
    CHECK(a.value_or(7) == 7);   // a 空，value_or 返回 7

    // make_optional 工厂
    auto c = tl::make_optional(std::string("tl"));
    CHECK(c.has_value());
    CHECK(c->size() == 2);

    // in_place 构造
    tl::optional<std::pair<int,int>> d(tl::in_place, 1, 2);
    CHECK(d->first == 1 && d->second == 2);

    // 扩展 API：map / and_then
    auto e = tl::optional<int>(3).map([](int v){ return v * 2; });
    CHECK(e.has_value() && e.value() == 6);
    auto f = tl::optional<int>(5).and_then([](int v) -> tl::optional<int> { return v > 4 ? tl::optional<int>(v+1) : tl::nullopt; });
    CHECK(f.has_value() && f.value() == 6);
    auto g = tl::optional<int>(1).and_then([](int) -> tl::optional<int> { return tl::nullopt; });
    CHECK(!g.has_value());

    // 比较运算符
    CHECK(tl::optional<int>(1) < tl::optional<int>(2));
    CHECK(tl::optional<int>(1) == tl::optional<int>(1));
    CHECK(tl::optional<int>(2) > tl::optional<int>(1));

    // reset / emplace / swap
    b.reset();
    CHECK(!b.has_value());
    b.emplace(99);
    CHECK(b.value() == 99);
    tl::optional<int> h(1), i(2);
    h.swap(i);
    CHECK(h.value() == 2 && i.value() == 1);

    std::printf("test_tl_optional PASS: %d checks OK\n", g_checks);
    return 0;
}
