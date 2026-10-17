// test_package/test_magic_enum.cpp — magic_enum 消费者测试
//
// 真实验证 magic_enum 0.9.7 的核心 API。每项断言失败即 return 1，
// 非仅 include + return 0 的空壳测试。
#include <magic_enum/magic_enum.hpp>

#include <cstdio>
#include <string>
#include <string_view>

namespace {
int g_failures = 0;

void check(bool cond, const char* label) {
    if (cond) {
        printf("[ok] %s\n", label);
    } else {
        printf("[FAIL] %s\n", label);
        ++g_failures;
    }
}
}  // namespace

enum class Color : int { RED = -10, BLUE = 0, GREEN = 10 };
enum class Permission { Read = 1, Write = 2, Execute = 4 };

int main() {
    // 1. enum_name: 枚举值 → 名称字符串
    auto green_name = magic_enum::enum_name(Color::GREEN);
    check(green_name == "GREEN", "enum_name(Color::GREEN) == \"GREEN\"");

    // 2. enum_cast: 名称字符串 → 枚举值（精确匹配）
    auto red_opt = magic_enum::enum_cast<Color>("RED");
    check(red_opt.has_value() && red_opt.value() == Color::RED,
          "enum_cast<Color>(\"RED\") == Color::RED");

    // 3. enum_cast: 大小写不敏感匹配
    auto blue_opt = magic_enum::enum_cast<Color>("blue", magic_enum::case_insensitive);
    check(blue_opt.has_value() && blue_opt.value() == Color::BLUE,
          "enum_cast<Color>(\"blue\", case_insensitive) == Color::BLUE");

    // 4. enum_values: 返回全部枚举值（顺序与声明一致）
    constexpr auto values = magic_enum::enum_values<Color>();
    check(values.size() == 3 && values[0] == Color::RED &&
              values[1] == Color::BLUE && values[2] == Color::GREEN,
          "enum_values<Color>() == {RED, BLUE, GREEN}");

    // 5. enum_count: 枚举值数量
    constexpr std::size_t count = magic_enum::enum_count<Color>();
    check(count == 3, "enum_count<Color>() == 3");

    // 6. enum_integer: 枚举值 → 底层整数值
    auto green_int = magic_enum::enum_integer(Color::GREEN);
    check(green_int == 10, "enum_integer(Color::GREEN) == 10");

    // 7. enum_name 对位标志枚举的基础支持（Permission::Write → "Write"）
    auto write_name = magic_enum::enum_name(Permission::Write);
    check(write_name == "Write", "enum_name(Permission::Write) == \"Write\"");

    if (g_failures == 0) {
        printf("\nmagic_enum smoke test: PASS (7/7 assertions OK)\n");
        return 0;
    }
    printf("\nmagic_enum smoke test: FAIL (%d assertion(s) failed)\n", g_failures);
    return 1;
}