// test_ctre.cpp — compile-time-regular 3.11.0 L1 冒烟测试
//
// 实质验证 CTRE 核心能力面（R34：调用被测包真实 API）：
//   1. C++17 核心路径：ctll::fixed_string NTTP + ctre::match/search
//      编译期正则实例化（CTRE_CNTTP_COMPILER_CHECK=false 的官方 C++17 路径）
//   2. 编译期捕获：constexpr 提取 + static_assert 断言匹配结果
//   3. 运行期接口：search/search_all/multiline、命名捕获组 get<"name">
//   4. 运行期断言（assert）：日期提取官方示例扩展
//
// 运行环境：HarmonyOS PC (aarch64, clang 15, libc++)，C++17。

#include <ctre.hpp>
#include <ctre/literals.hpp>

#include <cassert>
#include <cstdio>
#include <optional>
#include <string_view>

// ── 1. C++17 核心路径：fixed_string NTTP 编译期正则 ────────────────
static constexpr auto digits_pattern = ctll::fixed_string("[0-9]+");
static_assert(ctre::match<digits_pattern>("12345"), "compile-time match");

struct date { std::string_view year; std::string_view month; std::string_view day; };

static constexpr auto date_pattern = ctll::fixed_string("^([0-9]{4})/([0-9]{1,2}+)/([0-9]{1,2}+)$");

constexpr std::optional<date> extract_date(std::string_view s) noexcept {
    if (auto [whole, year, month, day] = ctre::match<date_pattern>(s); whole) {
        return date{year.to_view(), month.to_view(), day.to_view()};
    } else {
        return std::nullopt;
    }
}

// 编译期提取断言（核心卖点：全 constexpr 正则）
static_assert(extract_date("2018/08/27").has_value());
static_assert(extract_date("2018/08/27")->year == std::string_view("2018"));
static_assert(extract_date("2018/08/27")->month == std::string_view("08"));
static_assert(extract_date("2018/08/27")->day == std::string_view("27"));
static_assert(!extract_date("2018/8/27/1").has_value());

int main() {
    using namespace std::string_view_literals;

    // ── 1. C++17 编译期匹配（实例化 + static_assert 已在上方验证）──
    assert(ctre::match<digits_pattern>("12345"));
    assert(!ctre::match<digits_pattern>("abc"));

    // ── 2. 运行期日期提取（官方示例）──────────────────────────────
    auto d = extract_date("2018/08/27"sv);
    assert(d.has_value());
    assert(d->year == "2018"sv);
    assert(d->month == "08"sv);
    assert(d->day == "27"sv);

    // ── 3. search + 捕获组 to_view ─────────────────────────────────
    auto m = ctre::search<digits_pattern>("abc12345def"sv);
    assert(m);
    assert(m.to_view() == "12345"sv);

    // ── 4. 命名捕获组 get<"name"> ─────────────────────────────────
    static constexpr auto name_pattern =
        ctll::fixed_string("(?<first>[0-9])[0-9]++");
    auto nm = ctre::search<name_pattern>("123,456,768"sv);
    assert(nm);
    assert(nm.get<"first">() == "1"sv);
    assert(nm.get<1>() == "1"sv);

    // ── 5. search_all 区间迭代 ────────────────────────────────────
    int match_count = 0;
    for (auto match : ctre::search_all<name_pattern>("123,456,768"sv)) {
        assert(match.get<"first">().size() == 1);
        ++match_count;
    }
    assert(match_count == 3);

    // ── 6. starts_with / multiline 行为 ────────────────────────────
    static constexpr auto hello_pattern = ctll::fixed_string("hello");
    assert(ctre::starts_with<hello_pattern>("hello world"sv));
    assert(!ctre::match<hello_pattern>("hello world"sv));
    assert(ctre::multiline_match<hello_pattern>("hello\nworld"sv));

    std::printf("All CTRE 3.11.0 smoke tests passed\n");
    return 0;
}
