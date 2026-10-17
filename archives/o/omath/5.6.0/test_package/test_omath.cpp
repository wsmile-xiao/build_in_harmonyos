// Conan test_package for omath 5.6.0 — 真实消费者调用（R34 反空壳）。
//
// 四条检查各覆盖一项本包的适配面，删掉包内任一产物都会失败：
//   1. Angle<float, 0.f, 360.f>：上游核心模板的**浮点非类型模板参数**（clang15 编不了，
//      必须 tool_requires clang/22.1.8）；constexpr 求值证明打包头可用。
//   2. Vector3::angle_between：返回 std::expected<Angle<...>, Vector3Error>，
//      走本包交付的 <expected> 兼容头（libc++15 无该头）。
//   3. hashing::base64_{encode,decode}：非模板编译单元 + constexpr expected。
//   4. std::format(Angle)：formatter 特化在 omath 头里，依赖 -fexperimental-library
//      与链接期 libc++experimental（std::format_error 的 typeinfo/vtable/析构）。
#include <omath/hashing.hpp>
#include <omath/linear_algebra/vector3.hpp>
#include <omath/trigonometry/angle.hpp>

#include <cmath>
#include <format>
#include <iostream>
#include <string>

namespace
{
int fail(const char* what)
{
    std::cout << "omath consumer check FAILED: " << what << std::endl;
    return 1;
}
}  // namespace

int main()
{
    // 1) 浮点 NTTP 的 Angle：370° 归一化到 10°，并要求 constexpr 可求值
    using Deg = omath::Angle<float, static_cast<float>(0), static_cast<float>(360),
                             omath::AngleFlags::Normalized>;
    constexpr Deg wrapped = Deg::from_degrees(370.0f);
    static_assert(wrapped.as_degrees() == 10.0f, "Angle wrap must stay constexpr");
    if (wrapped.as_degrees() != 10.0f)
        return fail("Angle::from_degrees(370) did not wrap to 10");

    // 2) 向量夹角（std::expected 观察器路径）
    const omath::Vector3<float> x_axis{1.f, 0.f, 0.f};
    const omath::Vector3<float> y_axis{0.f, 1.f, 0.f};
    const auto right_angle = x_axis.angle_between(y_axis);
    if (!right_angle)
        return fail("Vector3::angle_between(x, y) returned an error");
    // 上游同款容差口径（tests/general/unit_test_vector3.cpp:482 用 EXPECT_NEAR(..., 90.0f, 0.001f)）
    if (std::fabs(right_angle->as_degrees() - 90.0f) > 0.001f)
        return fail("Vector3::angle_between(x, y) != 90 degrees");

    // 3) base64 往返（非模板编译单元 + constexpr expected）
    const auto decoded = omath::hashing::base64_decode("Zm9v");
    if (!decoded || *decoded != "foo")
        return fail("base64_decode(\"Zm9v\") != \"foo\"");
    if (omath::hashing::base64_encode("foo") != "Zm9v")
        return fail("base64_encode(\"foo\") != \"Zm9v\"");

    // 4) std::format formatter 特化
    const std::string formatted = std::format("{}", wrapped);
    if (formatted != "10deg")
        return fail("std::format(Angle) != \"10deg\"");

    std::cout << "omath consumer checks passed: angle=" << formatted
              << " between=" << right_angle->as_degrees() << "deg"
              << " base64=" << *decoded << std::endl;
    return 0;
}
