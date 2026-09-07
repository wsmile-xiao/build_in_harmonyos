// HarmonyOS 专项测试: au 0.6.0 on OHOS arm64 (toolchain /data/service/hnp/bin/clang++)
//
// 该测试不是上游测试的复述, 而是针对本次适配中实际产生差异的平台点做真实验证:
//   1. char 默认符号性 (arm64/OHOS 上 char 为 unsigned, 上游测试显式使用 signed char)
//   2. long double π 精度 (OHOS libc 不提供 M_PIl, au 自含 Pi::value())
//   3. 量纲运算 / 单位换算 / chrono 互操作的真实数值
//   4. root() 与 std::pow 的精度一致性 (OHOS powl 相对误差 ~1e-15)

#include "au/au.hh"
#include "au/chrono_interop.hh"
#include "au/units/feet.hh"
#include "au/units/grams.hh"
#include "au/units/joules.hh"
#include "au/units/meters.hh"
#include "au/units/newtons.hh"
#include "au/units/seconds.hh"
#include "au/utility/type_traits.hh"

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <type_traits>

using namespace au;

// 测试本地 Pack 容器, 置于独立命名空间以避免与 au::detail 重名。
namespace ohos_test {
template <typename... Ts>
struct Pack;
}

// 回归: 上游 type_traits_test.cc 的 `char` 在 arm64/OHOS 上默认为 unsigned,
// IncludeInPackIf 必须显式使用 signed char 才能得到 Pack<uint8_t, uint64_t>。
static bool check_char_signedness_regression() {
    using result = au::detail::IncludeInPackIf<std::is_unsigned, ohos_test::Pack, int32_t,
                                               uint8_t, double, signed char, uint64_t, int16_t>;
    return std::is_same<result, ohos_test::Pack<uint8_t, uint64_t>>::value;
}

// 回归: Pi::value() 必须等于高精度 π (OHOS 无 M_PIl)。
static bool check_pi_long_double() {
    const long double kPi = 3.141592653589793238462643383279502884L;
    return Pi::value() == kPi;
}

// 量纲运算真值验证: v = d / t; F = m * a (a = v / t)。
// `.in(Unit)` 接受 Unit 类型 (如 `meters / second`, `newtons`), 而非 QuantityMaker 调用。
static bool check_quantity_arithmetic() {
    const auto distance = meters(10.0) + meters(5.0);
    const auto speed = distance / seconds(3.0);
    const auto force = grams(2000.0) * (speed / seconds(1.0));
    return std::abs(speed.in(meters / second) / 1.0 - 5.0) < 1e-12 &&
           std::abs(force.in(newtons) - 10.0) < 1e-9;
}

// 单位换算: 10 feet -> meters。
static bool check_unit_conversion() {
    const auto d = feet(10.0).in(meters);
    return std::abs(d - 3.048) < 1e-12;
}

// chrono 互操作: std::chrono::milliseconds <-> au quantity 往返一致。
static bool check_chrono_interop() {
    const auto from_au = as_chrono_duration(seconds(2.5));
    const auto from_chrono = as_quantity(std::chrono::milliseconds{123});
    const auto round_trip = as_chrono_duration(from_chrono);
    return std::abs(static_cast<double>(from_au.count()) - 2.5) < 1e-12 &&
           round_trip.count() == 123;
}

// root() 与 std::pow 精度一致性 (OHOS powl 误差 ~1e-15 相对)。
static bool check_root_precision() {
    const double x = 5.67e25;
    const auto r = au::detail::root(x, 3u);
    const double ref = static_cast<double>(std::pow(x, 1.0L / 3.0L));
    return r.outcome == au::detail::MagRepresentationOutcome::OK &&
           std::abs(r.value - ref) / std::abs(ref) < 1e-12;
}

int main() {
    std::printf("target: OHOS arm64, char signed=%d unsigned=%d, sizeof(long double)=%zu\n",
                std::is_signed<char>::value, std::is_unsigned<char>::value,
                sizeof(long double));
    const bool checks[] = {
        check_char_signedness_regression(),
        check_pi_long_double(),
        check_quantity_arithmetic(),
        check_unit_conversion(),
        check_chrono_interop(),
        check_root_precision(),
    };
    const char *names[] = {
        "char_signedness_regression",
        "pi_long_double",
        "quantity_arithmetic",
        "unit_conversion",
        "chrono_interop",
        "root_precision",
    };
    int failed = 0;
    for (size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i) {
        std::printf("[%s] %s\n", checks[i] ? "PASS" : "FAIL", names[i]);
        if (!checks[i])
            ++failed;
    }
    std::printf("%zu checks, %d failed\n", sizeof(checks) / sizeof(checks[0]), failed);
    return failed == 0 ? 0 : 1;
}