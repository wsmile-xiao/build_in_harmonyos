/* test.c — dvector consumer test.
 *
 * dvector 是 header-only C99 数学库。本测试以消费者视角 include dvector.h，
 * 实际调用 vec3/quat/mat4/frst 接口并断言计算结果（R34：必须实质调用被测包 API）。
 * 使用 DVECTOR_ISOC 兼容模式（ISO C99 复合字面量）。
 */
#include <math.h>
#include <stdio.h>

#define DVECTOR_ISOC
#define DVECTOR_IMPLEMENTATION
#include <dvector.h>

static int failures = 0;

static void check(int condition, const char *description) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", description);
        failures++;
    }
}

static int approx(DVTYPE a, DVTYPE b) {
    return fabs(a - b) < (DVTYPE)1e-4;
}

int main(void) {
    /* vec3 基本运算 */
    vec3 a = VEC3(1.0f, 2.0f, 3.0f);
    vec3 b = VEC3(4.0f, 5.0f, 6.0f);
    vec3 sum = vec3Add(a, b);
    check(approx(sum.x, 5.0f) && approx(sum.y, 7.0f) && approx(sum.z, 9.0f),
          "vec3Add");
    vec3 diff = vec3Subtract(a, b);
    check(approx(diff.x, -3.0f) && approx(diff.y, -3.0f) && approx(diff.z, -3.0f),
          "vec3Subtract");
    DVTYPE dot = vec3DotProduct(a, b);
    check(approx(dot, 32.0f), "vec3DotProduct");
    vec3 cross = vec3CrossProduct(a, b);
    check(approx(cross.x, -3.0f) && approx(cross.y, 6.0f) && approx(cross.z, -3.0f),
          "vec3CrossProduct");
    DVTYPE len = vec3Length(VEC3(3.0f, 4.0f, 0.0f));
    check(approx(len, 5.0f), "vec3Length");
    vec3 norm = vec3Normalize(VEC3(3.0f, 4.0f, 0.0f));
    check(approx(norm.x, 0.6f) && approx(norm.y, 0.8f), "vec3Normalize");
    check(vec3Equal(VEC3(1.0f, 2.0f, 3.0f), a), "vec3Equal");
    check(!vec3Equal(a, b), "vec3Equal negative");

    /* quat：轴角四元数 + 旋转向量 */
    quat q = quatAxisAngle(VEC3(0.0f, 0.0f, 1.0f), (DVTYPE)(3.14159265f / 2.0f));
    vec3 v90 = quatMultiplyVector(q, VEC3(1.0f, 0.0f, 0.0f));
    check(approx(v90.x, 0.0f) && approx(v90.y, 1.0f) && approx(v90.z, 0.0f),
          "quatAxisAngle + quatMultiplyVector (90deg around Z)");
    quat qn = quatNormalize(QUAT(1.0f, 0.0f, 0.0f, 1.0f));
    check(approx(qn.w, (DVTYPE)(1.0f / sqrtf(2.0f))), "quatNormalize");

    /* mat4：单位阵 + 平移 + 变换向量 */
    mat4 id = MAT4_IDEN;
    check(mat4Equal(id, mat4MultiplyMatrix(id, id)), "mat4 identity multiply");
    mat4 tr = mat4SetTranslation(VEC3(1.0f, 2.0f, 3.0f));
    vec4 p = mat4MultiplyVector(tr, VEC4(0.0f, 0.0f, 0.0f, 1.0f));
    check(approx(p.x, 1.0f) && approx(p.y, 2.0f) && approx(p.z, 3.0f) && approx(p.w, 1.0f),
          "mat4 translation");
    mat4 rot = mat4SetRotationZ((DVTYPE)(3.14159265f / 2.0f));
    vec4 r = mat4MultiplyVector(rot, VEC4(1.0f, 0.0f, 0.0f, 1.0f));
    check(approx(r.x, 0.0f) && approx(r.y, 1.0f), "mat4SetRotationZ");

    /* frst：平截头体剔除 */
    mat4 proj = mat4Perspective((DVTYPE)(3.14159265f / 4.0f), 1.0f, 0.1f, 100.0f);
    frst f = frstFromMatrix(proj);
    check(frstCullSphere(f, VEC3(0.0f, 0.0f, -5.0f), 0.5f) == 1,
          "frstCullSphere inside");
    check(frstCullSphere(f, VEC3(50.0f, 0.0f, -5.0f), 0.1f) == 0,
          "frstCullSphere outside");

    if (failures == 0) {
        printf("dvector consumer test: ALL PASSED\n");
        return 0;
    }
    printf("dvector consumer test: %d FAILURES\n", failures);
    return 1;
}
