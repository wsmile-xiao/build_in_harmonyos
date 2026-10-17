// test_package/test_hlslpp.cpp — hlslpp 3.7 消费者端到端用例（rule12）
//
// 以真实消费者身份走完一个图形应用最典型的 HLSL 风格数学流程，而非单点断言：
//   1. 用 float4x4::look_at 构造视图矩阵，float4x4::perspective +
//      frustum::field_of_view_y 构造透视投影矩阵（HLSLPP_FEATURE_TRANSFORM）
//   2. 拼接 MVP 矩阵对世界空间顶点做变换，并与手写参照实现逐分量比对
//   3. 四元数 / 四元数转矩阵 / 旋转矩阵三条旋转路径互验，且与解析值一致
//   4. 用逆矩阵把裁剪空间坐标反投影回世界空间，验证回环精度
//   5. 验证整数向量与标量缩放路径同样可用
//
// hlslpp 约定（本用例依据库自身行为约定编写，已实测确认）：
//   - 逻辑布局默认行主序，乘法顺序为 mul(vector, matrix) / mul(vector, quaternion)；
//     实测元素映射为 out[c] = sum_r v[r] * m[r][c]
//   - 矩阵下标 m[c][r] 先列后行，故构造参数按行书写后会转置存放
//   - 默认左手坐标系，left/up/forward；绕 +Y 旋转 angle 得 (cos, 0, -sin)
//
// 任一步失败即返回非 0，结果由 test_package/conanfile.py 的 self.run() 采集。
#include <cmath>
#include <cstdio>

#include <hlsl++.h>

using namespace hlslpp;

static int g_failures = 0;

static void check(bool cond, const char* what) {
    if (!cond) {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    } else {
        std::printf("  ok: %s\n", what);
    }
}

static void checkf(float got, float want, float tol, const char* what) {
    if (std::fabs(got - want) > tol) {
        std::printf("FAIL: %s (got %.6f, want %.6f, tol %.6f)\n", what, got, want, tol);
        ++g_failures;
    } else {
        std::printf("  ok: %s (%.6f)\n", what, got);
    }
}

int main() {
    std::printf("hlslpp 3.7 consumer end-to-end test\n");

    // 后端自检：aarch64 应解析到 NEON 路径
#if defined(HLSLPP_ARM)
    std::printf("  backend: NEON (HLSLPP_ARM)\n");
#elif defined(HLSLPP_SSE)
    std::printf("  backend: SSE\n");
#elif defined(HLSLPP_SCALAR)
    std::printf("  backend: SCALAR\n");
#endif
    std::printf("  sizeof(float4x4) = %zu\n", sizeof(float4x4));

    // ---- 1. 视图 / 透视投影矩阵 -------------------------------------------
    const float3 eye(0.0f, 0.0f, -5.0f);   // 左手系：相机在 -Z 看向 +Z
    const float3 target(0.0f, 0.0f, 0.0f);
    const float3 up(0.0f, 1.0f, 0.0f);

    float4x4 view = float4x4::look_at(eye, target, up);

    const float aspect = 16.0f / 9.0f;
    const float fov_y  = 1.04719755f;      // 60 度
    frustum f = frustum::field_of_view_y(fov_y, aspect, 0.1f, 100.0f);
    float4x4 proj = float4x4::perspective(projection(f, zclip::zero));

    // 相机在 -Z、目标在原点：原点视图空间 z 应为 +5（左手系前方为正）
    float4 origin_vs = mul(float4(0.0f, 0.0f, 0.0f, 1.0f), view);
    checkf(origin_vs.x, 0.0f, 1e-5f, "look_at: origin view x");
    checkf(origin_vs.y, 0.0f, 1e-5f, "look_at: origin view y");
    checkf(origin_vs.z, 5.0f, 1e-5f, "look_at: origin view z");

    // ---- 2. MVP 拼接 + 顶点变换（与手写参照比对）--------------------------
    // 行主序约定：v * (view * proj)
    float4x4 mvp = mul(view, proj);
    float4 world(1.0f, 2.0f, 3.0f, 1.0f);
    float4 clip = mul(world, mvp);

    // 手写参照：out[c] = sum_r v[r] * m[r][c]（已实测确认 mul(v,m) 的元素映射）
    float manual[4];
    for (int c = 0; c < 4; ++c) {
        float acc = 0.0f;
        for (int r = 0; r < 4; ++r) {
            acc += world[r] * mvp[r][c];
        }
        manual[c] = acc;
    }
    checkf(clip.x, manual[0], 1e-5f, "mvp: clip.x == manual");
    checkf(clip.y, manual[1], 1e-5f, "mvp: clip.y == manual");
    checkf(clip.z, manual[2], 1e-5f, "mvp: clip.z == manual");
    checkf(clip.w, manual[3], 1e-5f, "mvp: clip.w == manual");
    // 透视投影下裁剪空间 w 等于视图空间 z；目标在相机前方故 w > 0
    check(clip.w > 0.0f, "mvp: clip.w > 0 (in front of camera)");
    // 世界点 (1,2,3) 在相机 (0,0,-5) 前方，透视后应落在近/远平面之间
    check(clip.z > 0.0f, "mvp: clip.z > 0 (inside near plane)");

    // ---- 3. 三条旋转路径互验 + 解析值 -------------------------------------
    const float angle = 0.64577182f;       // 37 度
    const float3 axis_y(0.0f, 1.0f, 0.0f);
    float3 vx(1.0f, 0.0f, 0.0f);

    quaternion q_axis = quaternion::rotation_axis(axis_y, angle);
    quaternion q_rot  = quaternion::rotation_y(angle);
    float3x3   m_rot  = float3x3::rotation_y(angle);

    float3 v_quat  = mul(vx, q_axis);      // 路径 a：四元数直接旋转
    float3 v_quat2 = mul(vx, q_rot);       // 路径 b：四元数工厂函数
    float3 v_mat   = mul(vx, m_rot);       // 路径 c：旋转矩阵
    float3 v_q2m   = mul(vx, float3x3(q_axis));   // 路径 d：四元数转矩阵

    checkf(v_quat.x, v_quat2.x, 1e-5f, "quat(axis) vs quat(rotation_y): x");
    checkf(v_quat.z, v_quat2.z, 1e-5f, "quat(axis) vs quat(rotation_y): z");
    checkf(v_quat.x, v_mat.x, 1e-5f, "quat vs rotation matrix: x agrees");
    checkf(v_quat.y, v_mat.y, 1e-5f, "quat vs rotation matrix: y agrees");
    checkf(v_quat.z, v_mat.z, 1e-5f, "quat vs rotation matrix: z agrees");
    checkf(v_quat.x, v_q2m.x, 1e-5f, "quat vs quat->matrix: x agrees");
    checkf(v_quat.z, v_q2m.z, 1e-5f, "quat vs quat->matrix: z agrees");
    // 左手系绕 +Y 旋转 angle：x' = cos(a), z' = -sin(a)
    checkf(v_quat.x, std::cos(angle), 1e-5f, "quat rotate: x == cos(37deg)");
    checkf(v_quat.z, -std::sin(angle), 1e-5f, "quat rotate: z == -sin(37deg)");

    // 旋转保长：|R*v| == |v|
    float len_in  = std::sqrt(vx.x * vx.x + vx.y * vx.y + vx.z * vx.z);
    float len_out = std::sqrt(v_quat.x * v_quat.x + v_quat.y * v_quat.y +
                              v_quat.z * v_quat.z);
    checkf(len_out, len_in, 1e-5f, "quat rotation preserves length");

    // ---- 4. 逆矩阵回环：世界 -> 裁剪 -> 世界 ------------------------------
    float4x4 inv_mvp = inverse(mvp);
    float4 back = mul(clip, inv_mvp);
    checkf(back.x, world.x, 1e-3f, "round-trip: x restored");
    checkf(back.y, world.y, 1e-3f, "round-trip: y restored");
    checkf(back.z, world.z, 1e-3f, "round-trip: z restored");
    checkf(back.w, world.w, 1e-3f, "round-trip: w restored");

    // det(M) * det(inv(M)) == 1
    checkf(determinant(mvp) * determinant(inv_mvp), 1.0f, 1e-3f,
           "det(M) * det(inv(M)) == 1");

    // 变换矩阵组合律：(v*A)*B == v*(A*B)
    float4x4 ab = mul(view, proj);
    float4 via_chained = mul(mul(world, view), proj);
    float4 via_combined = mul(world, ab);
    checkf(via_chained.x, via_combined.x, 1e-4f, "associativity: x");
    checkf(via_chained.y, via_combined.y, 1e-4f, "associativity: y");
    checkf(via_chained.z, via_combined.z, 1e-4f, "associativity: z");
    checkf(via_chained.w, via_combined.w, 1e-4f, "associativity: w");

    // ---- 5. 其他类型路径在 aarch64 上可用 ---------------------------------
    int4 iv(3, -5, 7, 11);
    int4 iv2 = iv * int4(2, 2, 2, 2);
    check(iv2.x == 6 && iv2.y == -10 && iv2.z == 14 && iv2.w == 22,
          "int4 scalar multiply");

    float2x2 scaled = float2x2::scale(2.0f, 3.0f);
    float2 sv = mul(float2(1.0f, 1.0f), scaled);
    checkf(sv.x, 2.0f, 1e-6f, "float2x2::scale x");
    checkf(sv.y, 3.0f, 1e-6f, "float2x2::scale y");

    if (g_failures != 0) {
        std::printf("\nhlslpp consumer test FAILED: %d check(s) failed\n", g_failures);
        return 1;
    }
    std::printf("\nhlslpp 3.7 consumer end-to-end test PASSED (all checks ok)\n");
    return 0;
}
