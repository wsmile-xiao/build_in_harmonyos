// gcem 1.16.0 — HarmonyOS-specific test (R02)
// 在 OHOS (aarch64) 工具链下编译运行，验证:
//   1) 平台宏 __OHOS__ 与 __aarch64__ 已定义（确认目标为 HarmonyOS aarch64 平台）
//   2) header-only gcem 头文件在 OHOS 平台上真实调用 gcem:: API（编译期 constexpr + 运行期数值）
#include <cassert>
#include <cmath>
#include <cstdio>

#if !defined(__OHOS__)
#error "harmonyos_specific_test: __OHOS__ not defined — not compiled for HarmonyOS platform"
#endif
#if !defined(__aarch64__)
#error "harmonyos_specific_test: __aarch64__ not defined — not HarmonyOS aarch64 target"
#endif

#include "gcem.hpp"

// 编译期 constexpr 断言（在 OHOS 平台编译期求值）
static_assert(gcem::abs(-7) == 7, "gcem::abs constexpr failed (OHOS)");
static_assert(gcem::sqrt(16.0) == 4.0, "gcem::sqrt constexpr failed (OHOS)");
static_assert(gcem::log(1.0) == 0.0, "gcem::log constexpr failed (OHOS)");
static_assert(gcem::pow(3, 3) == 27, "gcem::pow constexpr failed (OHOS)");

int main() {
    // 运行期真实调用 gcem API，并与 std 精度对齐
    const double x = 2.5;
    assert(std::abs(gcem::exp(x) - std::exp(x)) < 1e-12);
    assert(std::abs(gcem::log(x) - std::log(x)) < 1e-12);
    assert(std::abs(gcem::sin(x) - std::sin(x)) < 1e-12);
    assert(std::abs(gcem::cos(x) - std::cos(x)) < 1e-12);
    assert(std::abs(gcem::sqrt(x) - std::sqrt(x)) < 1e-12);
    assert(std::abs(gcem::tan(x) - std::tan(x)) < 1e-12);

    std::printf("harmonyos_specific_test OK: platform=OHOS(aarch64) __OHOS__/__aarch64__ defined, "
                "gcem API constexpr+runtime checks passed\n");
    return 0;
}
