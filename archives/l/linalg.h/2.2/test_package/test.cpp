// test_package consumer test for linalg.h 2.2 (header-only).
// Real API usage: vector algebra, matrix multiplication, quaternions,
// constexpr evaluation — exercising the actual packaged header (R34).
#include <linalg.h>
#include <cassert>
#include <cmath>
#include <iostream>

using namespace linalg::aliases;

int main()
{
    // Vector arithmetic: (1,2,3) + (4,5,6) = (5,7,9)
    float3 a{1.f, 2.f, 3.f};
    float3 b{4.f, 5.f, 6.f};
    float3 c = a + b;
    assert(c.x == 5.f && c.y == 7.f && c.z == 9.f);

    // Dot product: (1,2,3) . (4,5,6) = 32
    assert(std::fabs(dot(a, b) - 32.f) < 1e-6f);

    // Cross product: (1,2,3) x (4,5,6) = (-3,6,-3)
    float3 x = cross(a, b);
    assert(std::fabs(x.x + 3.f) < 1e-6f);
    assert(std::fabs(x.y - 6.f) < 1e-6f);
    assert(std::fabs(x.z + 3.f) < 1e-6f);

    // Matrix * vector: identity leaves vector unchanged
    float3x3 m = linalg::identity;
    float3 r = mul(m, a);
    assert(r.x == a.x && r.y == a.y && r.z == a.z);

    // Matrix multiplication: (2*2)*(2*2) dimensions
    float2x2 ma{{1.f, 0.f}, {0.f, 1.f}};
    float2x2 mb{{2.f, 0.f}, {0.f, 2.f}};
    float2x2 mc = mul(ma, mb);
    assert(mc.x.x == 2.f && mc.y.y == 2.f);

    // Quaternion: rotate (1,0,0) by 180 deg around Z -> (-1,0,0)
    float4 q = rotation_quat(float3{0.f, 0.f, 1.f}, 3.14159265358979f);
    float4 v{1.f, 0.f, 0.f, 0.f};
    float4 rv = qmul(qmul(q, v), qconj(q));
    assert(std::fabs(rv.x + 1.f) < 1e-4f);
    assert(std::fabs(rv.y) < 1e-4f);

    // Constexpr evaluation
    constexpr float3 ce = float3{1.f, 2.f, 3.f} + float3{4.f, 5.f, 6.f};
    static_assert(ce.x == 5.f && ce.y == 7.f && ce.z == 9.f, "constexpr vec add");

    std::cout << "linalg.h 2.2 consumer test: OK" << std::endl;
    return 0;
}
