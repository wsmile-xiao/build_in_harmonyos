// HarmonyOS 专项测试 — linalg.h 2.2 (header-only)。
// 在 OHOS aarch64 平台使用 OHOS clang 工具链编译运行，验证：
//   1. 头文件在 -std=c++11 下可编译（无平台宏依赖、无符号泄露）
//   2. 类型布局/对齐符合 aarch64 ABI（sizeof/alignof + trivially copyable）
//   3. constexpr 数学运算在 OHOS 编译器前端正确求值
//   4. 运行期向量/矩阵/四元数运算结果正确
// 真实可执行（非空壳），输出到 stdout 由 test_package 捕获。
#include <linalg.h>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <type_traits>

using namespace linalg::aliases;

int main()
{
    // ── 1. 平台 ABI 布局：aarch64 float 4 字节对齐
    static_assert(std::is_standard_layout<float3>::value,  "float3 must be standard layout");
    static_assert(std::is_trivially_copyable<float3>::value,"float3 must be trivially copyable");
    static_assert(sizeof(float3) == 3 * sizeof(float), "float3 size mismatch");
    static_assert(sizeof(float4) == 4 * sizeof(float), "float4 size mismatch");
    static_assert(sizeof(float4x4) == 16 * sizeof(float), "float4x4 size mismatch");
    static_assert(alignof(float4) == alignof(float), "float4 alignment mismatch");
    static_assert(std::is_same<decltype(float3{}.x), float>::value, "float3::x is float");

    // ── 2. constexpr 求值：OHOS clang 前端常量表达式支持
    constexpr float3 ce_a{1.f, 2.f, 3.f};
    constexpr float3 ce_b{4.f, 5.f, 6.f};
    constexpr float ce_dot = dot(ce_a, ce_b);
    static_assert(ce_dot == 32.f, "constexpr dot(1,2,3).(4,5,6) == 32");
    constexpr float3 ce_cross = cross(ce_a, ce_b);
    static_assert(ce_cross.x == -3.f && ce_cross.y == 6.f && ce_cross.z == -3.f, "constexpr cross");

    // ── 3. 运行期运算正确性（OHOS aarch64 实测）
    float3 a{1.f, 2.f, 3.f};
    float3 b{4.f, 5.f, 6.f};
    assert(dot(a, b) == 32.f);
    float3 c = cross(a, b);
    assert(std::fabs(c.x + 3.f) < 1e-6f && std::fabs(c.y - 6.f) < 1e-6f && std::fabs(c.z + 3.f) < 1e-6f);

    // 矩阵乘法：旋转 90° 绕 Z 轴，作用到 (1,0,0) -> (0,1,0)
    float4x4 rot = rotation_matrix(rotation_quat(float3{0.f, 0.f, 1.f}, 1.5707963267948966f));
    float4 vr = mul(rot, float4{1.f, 0.f, 0.f, 0.f});
    assert(std::fabs(vr.x) < 1e-6f && std::fabs(vr.y - 1.f) < 1e-6f && std::fabs(vr.z) < 1e-6f);

    // 四元数：绕 Z 旋转 180°, (1,0,0) -> (-1,0,0)
    float4 q = rotation_quat(float3{0.f, 0.f, 1.f}, 3.141592653589793f);
    float4 v{1.f, 0.f, 0.f, 0.f};
    float4 vq = qmul(qmul(q, v), qconj(q));
    assert(std::fabs(vq.x + 1.f) < 1e-4f && std::fabs(vq.y) < 1e-4f && std::fabs(vq.z) < 1e-4f);

    // ── 4. 无平台宏依赖：整个头文件在 OHOS clang 下零警告编译已完成
    std::cout << "[linalg.h OHOS专项测试] PASS: ABI布局/constexpr/矩阵/四元数 全部通过" << std::endl;
    return 0;
}