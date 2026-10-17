#include <cassert>
#include <iostream>
#include <string_view>
#include <fix8/conjure_enum.hpp>
#include <fix8/conjure_enum_bitset.hpp>
#include <fix8/conjure_type.hpp>

enum class component : int { scheme, authority, userinfo, user, password, host, port, path = 12, test = path, query, fragment };
enum class numbers : int { zero, one, two, three, four, five, six, seven, eight, nine };

int main() {
    using CE = FIX8::conjure_enum<component>;

    // conjure_enum: 枚举↔字符串反射（真实 API 调用）
    static_assert(CE::entries.size() == CE::count(), "entries/count consistency");

    // enum_to_string<T e>() 返回 std::string_view（scoped 名）
    constexpr std::string_view sv_scheme { CE::enum_to_string<component::scheme>() };
    assert(sv_scheme == "component::scheme");
    if (CE::enum_to_string<component::port>() != "component::port") return 1;

    // string_to_enum: 字符串 → 枚举
    auto parsed = CE::string_to_enum("component::path");
    assert(parsed == component::path);
    if (!parsed) return 2;
    if (CE::string_to_enum("bogus")) return 3;

    // contains
    assert(CE::contains("component::fragment"));
    if (!CE::contains(component::scheme)) return 4;

    // enum <==> int
    if (CE::enum_to_int(component::fragment) != 14) return 5;
    auto from_int = CE::int_to_enum(12);
    if (!from_int || *from_int != component::path) return 6;

    // conjure_type: 类型名反射（真实 API 调用；name 为 fixed_string）
    constexpr std::string_view tn { FIX8::conjure_type<component>::name };
    assert(tn.find("component") != std::string_view::npos);
    if (tn.find("component") == std::string_view::npos) return 7;

    // enum_bitset: 位集合（真实 API 调用；需 0 基连续枚举）
    FIX8::enum_bitset<numbers> eb(numbers::zero, numbers::two);
    assert(eb.test(numbers::zero));
    if (!eb.test(numbers::two)) return 8;
    if (eb.test(numbers::three)) return 9;
    eb.set(numbers::three);
    if (!eb.test(numbers::three)) return 10;
    eb.reset(numbers::two);
    if (eb.test(numbers::two)) return 11;
    if (eb.to_string() != "0000001001") return 12;  // bit3 + bit0 置位（MSB-first）

    std::cout << "test_conjure_enum: OK (count=" << CE::count() << ", entries="
              << CE::entries.size() << ", type=" << tn << ")\n";
    return 0;
}