// gcem 1.16.0 test_package — 消费方视角 L1 测试
// 验证 header-only gcem 头文件在编译期 (constexpr) 与运行期均可使用。
#include <cassert>
#include <cmath>
#include <iostream>

#include "gcem.hpp"

// 编译期常量表达式断言
static_assert(gcem::abs(-5) == 5, "gcem::abs constexpr failed");
static_assert(gcem::abs(3.5) == 3.5, "gcem::abs(double) constexpr failed");
static_assert(gcem::sqrt(9.0) == 3.0, "gcem::sqrt constexpr failed");
static_assert(gcem::pow(2, 4) == 16, "gcem::pow constexpr failed");
static_assert(gcem::min(1, 2) == 1, "gcem::min constexpr failed");
static_assert(gcem::max(1, 2) == 2, "gcem::max constexpr failed");

int main() {
    // 运行期数值与标准库精度对齐抽查
    assert(std::abs(gcem::exp(1.0) - std::exp(1.0)) < 1e-12);
    assert(std::abs(gcem::log(2.0) - std::log(2.0)) < 1e-12);
    assert(std::abs(gcem::sin(0.5) - std::sin(0.5)) < 1e-12);
    assert(std::abs(gcem::cos(0.5) - std::cos(0.5)) < 1e-12);
    std::cout << "gcem test_package OK: constexpr and runtime checks passed" << std::endl;
    return 0;
}