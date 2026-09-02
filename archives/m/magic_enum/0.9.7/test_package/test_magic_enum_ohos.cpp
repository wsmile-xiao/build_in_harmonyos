// test_package/test_magic_enum_ohos.cpp — magic_enum 鸿蒙特有测试
//
// 在 HarmonyOS PC (aarch64-unknown-linux-ohos) 目标上验证 magic_enum 的
// 真实兼容行为：
//   1) __OHOS__ 平台宏存在（确认编译目标是鸿蒙）
//   2) OHOS/Linux ABI 特征：wchar_t 4 字节、char16_t 2 字节、指针 8 字节
//      （与 Windows 的 wchar_t 2 字节、32 位指针形成平台差异）
//   3) 真实调用 magic_enum 核心 API：enum_name / enum_cast / enum_values /
//      enum_count / enum_integer，以及 flags API：enum_flags_name /
//      enum_flags_cast（魔术枚举反射在鸿蒙上的可运行性）
// 每项断言失败即 return 1，非仅 include + return 0 的空壳测试。
#include <magic_enum/magic_enum.hpp>
#include <magic_enum/magic_enum_flags.hpp>

#include <cstdint>
#include <cstdio>
#include <string>

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

// 真实业务枚举：OHOS 常见返回码风格（负值 + 非连续，超出 magic_enum
// 默认范围 [-128,127]，需定制 enum_range 才能在 OHOS 上完整反射）
enum class OhosStatus : int {
    OK = 0,
    ERR_NO_PERM = -201,
    ERR_INVALID_PARAM = -401,
    ERR_TIMEOUT = -2301,
};

template <>
struct magic_enum::customize::enum_range<OhosStatus> {
    static constexpr int min = -2301;
    static constexpr int max = 0;
};

// flags 位标志枚举
enum class AccessFlags : unsigned {
    None = 0,
    Read = 1 << 0,
    Write = 1 << 1,
    Execute = 1 << 2,
};

template <>
struct magic_enum::customize::enum_range<AccessFlags> {
    static constexpr bool is_flags = true;
};

using namespace magic_enum;
using namespace magic_enum::bitwise_operators;

int main() {
    // 1) 平台确认
#ifdef __OHOS__
    check(true, "__OHOS__ defined (HarmonyOS target)");
#else
    check(false, "__OHOS__ should be defined on HarmonyOS target");
#endif
    check(sizeof(wchar_t) == 4, "wchar_t == 4 bytes (OHOS/Linux ABI)");
    check(sizeof(char16_t) == 2, "char16_t == 2 bytes");
    check(sizeof(void*) == 8, "pointer == 8 bytes (aarch64)");

    // 2) enum_name: 枚举值 -> 名称（含负值、非连续）
    check(magic_enum::enum_name(OhosStatus::OK) == "OK",
          "enum_name(OK) == \"OK\"");
    check(magic_enum::enum_name(OhosStatus::ERR_NO_PERM) == "ERR_NO_PERM",
          "enum_name(ERR_NO_PERM) == \"ERR_NO_PERM\"");
    check(magic_enum::enum_name(OhosStatus::ERR_TIMEOUT) == "ERR_TIMEOUT",
          "enum_name(ERR_TIMEOUT) == \"ERR_TIMEOUT\"");

    // 3) enum_cast: 名称 -> 枚举值（精确 + 大小写不敏感）
    auto p = magic_enum::enum_cast<OhosStatus>("ERR_INVALID_PARAM");
    check(p.has_value() && p.value() == OhosStatus::ERR_INVALID_PARAM,
          "enum_cast<OhosStatus>(\"ERR_INVALID_PARAM\") == ERR_INVALID_PARAM");
    auto ci = magic_enum::enum_cast<OhosStatus>("err_no_perm",
                                                magic_enum::case_insensitive);
    check(ci.has_value() && ci.value() == OhosStatus::ERR_NO_PERM,
          "enum_cast<OhosStatus>(\"err_no_perm\", case_insensitive) == ERR_NO_PERM");

    // 4) enum_values / enum_count
    constexpr auto vals = magic_enum::enum_values<OhosStatus>();
    check(vals.size() == 4, "enum_values<OhosStatus>().size() == 4");
    check(magic_enum::enum_count<OhosStatus>() == 4, "enum_count == 4");

    // 5) enum_integer
    check(magic_enum::enum_integer(OhosStatus::ERR_NO_PERM) == -201,
          "enum_integer(ERR_NO_PERM) == -201");
    check(magic_enum::enum_integer(OhosStatus::ERR_TIMEOUT) == -2301,
          "enum_integer(ERR_TIMEOUT) == -2301");

    // 6) flags: enum_flags_name / enum_flags_cast
    const AccessFlags rw = AccessFlags::Read | AccessFlags::Write;
    check(magic_enum::enum_flags_name(rw) == "Read|Write",
          "enum_flags_name(Read|Write) == \"Read|Write\"");
    auto fc = magic_enum::enum_flags_cast<AccessFlags>("Execute|Read");
    check(fc.has_value() && fc.value() == (AccessFlags::Read | AccessFlags::Execute),
          "enum_flags_cast<AccessFlags>(\"Execute|Read\") == Read|Execute");

    if (g_failures == 0) {
        printf("\nmagic_enum OHOS compat test: PASS (14/14 assertions OK)\n");
        return 0;
    }
    printf("\nmagic_enum OHOS compat test: FAIL (%d assertion(s) failed)\n",
           g_failures);
    return 1;
}