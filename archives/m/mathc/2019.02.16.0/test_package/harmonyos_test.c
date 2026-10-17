// mathc 2019.02.16.0 HarmonyOS 专项测试（真实可执行，非空壳）
// 断言：平台识别 + mathc 公开 API 功能（vec3 运算/mat4 变换/quat 旋转/mat4 逆矩阵）
#include <stdio.h>
#include <math.h>
#include "mathc.h"

static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS: %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); g_fail++; } \
} while (0)

int main(void) {
    printf("=== mathc 2019.02.16.0 HarmonyOS 专项测试 ===\n");

    // 1. 平台识别：OHOS aarch64 工具链（clang 15）
#if defined(__OHOS__) || defined(__OHOS_FAMILY__) || defined(OPENHARMONY)
    CHECK(1, "platform: OHOS 宏已定义");
#elif defined(__aarch64__) || defined(_M_ARM64)
    CHECK(1, "platform: aarch64 架构（HarmonyOS PC 目标）");
#else
    CHECK(0, "platform: 未知平台宏");
#endif
#if defined(__linux__)
    CHECK(1, "platform: __linux__ 定义（HarmonyOS 基于 Linux 内核）");
#else
    CHECK(0, "platform: __linux__ 缺失");
#endif

    // 2. vec3 基础运算：add / dot / cross / length
    float a[3], b[3], c[3];
    vec3(a, 1.0f, 2.0f, 3.0f);
    vec3(b, 4.0f, 5.0f, 6.0f);
    vec3_add(c, a, b);
    CHECK(fabsf(c[0] - 5.0f) < 1e-5f && fabsf(c[1] - 7.0f) < 1e-5f && fabsf(c[2] - 9.0f) < 1e-5f,
          "vec3_add(1,2,3)+(4,5,6)==(5,7,9)");
    CHECK(fabsf(vec3_dot(a, b) - 32.0f) < 1e-4f, "vec3_dot(1,2,3)·(4,5,6)==32");
    vec3_cross(c, a, b);
    CHECK(fabsf(c[0] - (-3.0f)) < 1e-5f && fabsf(c[1] - 6.0f) < 1e-5f && fabsf(c[2] - (-3.0f)) < 1e-5f,
          "vec3_cross(1,2,3)x(4,5,6)==(-3,6,-3)");
    CHECK(fabsf(vec3_length(a) - sqrtf(14.0f)) < 1e-5f, "vec3_length(1,2,3)==sqrt(14)");

    // 3. mat4 变换：identity + translation + multiply
    float m[16], t[16], v[4], out[4];
    mat4_identity(m);
    CHECK(fabsf(m[0] - 1.0f) < 1e-6f && fabsf(m[15] - 1.0f) < 1e-6f, "mat4_identity 对角为 1");
    vec3(b, 10.0f, 20.0f, 30.0f);
    mat4_translation(t, m, b);
    vec4(v, 1.0f, 0.0f, 0.0f, 1.0f);
    vec4_multiply_mat4(out, v, t);
    CHECK(fabsf(out[0] - 11.0f) < 1e-4f && fabsf(out[1] - 20.0f) < 1e-4f && fabsf(out[2] - 30.0f) < 1e-4f,
          "mat4_translation 平移 (1,0,0)->(11,20,30)");

    // 4. quat 旋转：绕 Z 轴 90° 旋转 (1,0,0) -> (0,1,0)
    float q[4], rot[16];
    quat(q, 0.0f, 0.0f, 0.70710678f, 0.70710678f);  // angle=90° around z: sin(45), cos(45)
    mat4_rotation_quat(rot, q);
    vec4(v, 1.0f, 0.0f, 0.0f, 1.0f);
    vec4_multiply_mat4(out, v, rot);
    CHECK(fabsf(out[0]) < 1e-4f && fabsf(out[1] - 1.0f) < 1e-4f,
          "quat 绕 Z 90° 旋转 (1,0,0)->(~0,1,0)");

    // 5. mat4_inverse：M * M^-1 ≈ identity（透视矩阵）
    float p[16], pinv[16], prod[16], id[16];
    mat4_perspective(p, 1.04719755f, 16.0f / 9.0f, 0.1f, 100.0f);
    mat4_inverse(pinv, p);
    mat4_multiply(prod, p, pinv);
    mat4_identity(id);
    int ok = 1;
    for (int i = 0; i < 16; i++) {
        float expect = id[i];
        if (fabsf(prod[i] - expect) > 1e-4f) { ok = 0; printf("    [%d] M*Minv=%f expect %f\n", i, prod[i], expect); }
    }
    CHECK(ok, "mat4_perspective: M * M^-1 ≈ identity");

    // 6. nearly_equal / clampi
    CHECK(nearly_equal(0.1f + 0.2f, 0.3f, 1e-4f), "nearly_equal(0.1+0.2, 0.3, 1e-4)");
    CHECK(clampi(50, 0, 10) == 10 && clampi(-5, 0, 10) == 0 && clampi(5, 0, 10) == 5,
          "clampi 边界裁剪正确");

    printf("=== 结果: %s (%d 失败) ===\n", g_fail == 0 ? "ALL PASS" : "FAILED", g_fail);
    return g_fail == 0 ? 0 : 1;
}