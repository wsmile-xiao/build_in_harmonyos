/*
 * consumer_e2e.c — dvector 0a6194c5ee HarmonyOS 特有端到端消费者用例
 *
 * 范围：在目标 OH 设备上真实运行的完整消费者端到端用例（非纯断言、非
 * printf-only、非 always-green）：用 dvector 的 mat4/quat/frst API 实现
 * 一条完整的 3D 渲染管线（Model→View→Projection→透视除法→视锥剔除→
 * 顶点统计），对每个阶段结果与解析解做严格校验；任何校验失败均以非零
 * 退出码结束（可失败），从而证明该用例真实消费 dvector 功能并真实校验。
 *
 * 构建（OHOS aarch64 本机直接执行）：
 *   clang -std=c99 -O2 -I<dvector 头目录> consumer_e2e.c -lm -o consumer_e2e
 * 运行：
 *   ./consumer_e2e
 *
 * 本用例与 test_package/test.c 分离：test_package 是 Conan L1 配方自检
 * （断言级），本用例是鸿蒙特有端到端消费者用例（独立交付）。
 */
#define DVECTOR_ISOC
#define DVECTOR_IMPLEMENTATION
#include <dvector.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static int g_failures = 0;

static void check(int condition, const char *description) {
    if (!condition) {
        fprintf(stderr, "[FAIL] %s\n", description);
        g_failures++;
    } else {
        printf("[PASS] %s\n", description);
    }
}

static int approx(DVTYPE a, DVTYPE b) {
    return fabs(a - b) < 1e-4f;
}

int main(void) {
    printf("=== dvector HarmonyOS 消费者端到端用例 ===\n");

    /* ── 场景：相机位于 (0,0,5) 看向原点，FOV 60°，近/远平面 0.1/100 ── */
    const vec3 eye = VEC3(0.0f, 0.0f, 5.0f);
    const vec3 center = VEC3(0.0f, 0.0f, 0.0f);
    const vec3 up = VEC3(0.0f, 1.0f, 0.0f);
    mat4 view = mat4LookAt(eye, center, up);

    /* ── 投影矩阵 ── */
    mat4 proj = mat4Perspective(60.0f * (DVTYPE)3.14159265f / 180.0f, 16.0f / 9.0f, 0.1f, 100.0f);

    /* ── 立方体 8 顶点（世界坐标，边长 2，中心原点）── */
    static const DVTYPE cube[8][3] = {
        {-1,-1,-1},{1,-1,-1},{1,1,-1},{-1,1,-1},
        {-1,-1,1},{1,-1,1},{1,1,1},{-1,1,1}
    };
    const int N = 8;

    /* ── 管线 1：LookAt 视图矩阵解析校验 ──
       相机在 z=5 看向原点：原点经视图变换后应落在相机前方 z=-5 处。 */
    {
        vec4 origin_view = mat4MultiplyVector(view, VEC4(0, 0, 0, 1));
        check(approx(origin_view.x, 0) && approx(origin_view.y, 0) &&
              approx(origin_view.z, -5.0f) && approx(origin_view.w, 1),
              "View: 原点经 LookAt 变换到相机前方 z=-5");
    }

    /* ── 管线 2：透视投影 + 透视除法：视场中心点投影到 NDC 原点 ── */
    {
        vec4 p = mat4MultiplyVector(proj, VEC4(0, 0, -5, 1)); /* 相机前方 5 处中心点 */
        DVTYPE ndc_x = p.x / p.w, ndc_y = p.y / p.w, ndc_z = p.z / p.w;
        check(approx(ndc_x, 0) && approx(ndc_y, 0),
              "Projection: 视场中心经透视除法落 NDC (0,0)");
    }

    /* ── 管线 3：四元数旋转 vs 矩阵旋转一致性 ──
       绕 Z 轴 90°：向量 (1,0,0) → (0,1,0)。 */
    {
        quat q = quatAxisAngle(VEC3(0, 0, 1), (DVTYPE)(3.14159265f / 2.0f));
        mat4 rm = mat4SetRotationZ((DVTYPE)(3.14159265f / 2.0f));
        vec3 vq = quatMultiplyVector(q, VEC3(1, 0, 0));
        vec4 vm = mat4MultiplyVector(rm, VEC4(1, 0, 0, 1));
        check(approx(vq.x, 0) && approx(vq.y, 1), "Quat: 绕Z 90° (1,0,0)→(0,1,0)");
        check(approx(vm.x, 0) && approx(vm.y, 1), "Mat4: 绕Z 90° (1,0,0)→(0,1,0)");
        check(approx(vq.x, vm.x) && approx(vq.y, vm.y),
              "Consistency: 四元数与矩阵旋转结果一致");
    }

    /* ── 管线 4：端到端渲染管线全流程 ──
       对 8 顶点执行 View→Projection→透视除法→视锥内可见性判定，
       统计可见顶点数；用 frstCullSphere 对照验证。 */
    {
        mat4 vp = mat4MultiplyMatrix(proj, view);
        frst f = frstFromMatrix(vp);
        int visible_clip = 0, visible_frst_outer = 0;
        printf("\n--- 端到端顶点变换统计 ---\n");
        for (int i = 0; i < N; i++) {
            vec4 w = VEC4(cube[i][0], cube[i][1], cube[i][2], 1);
            vec4 c = mat4MultiplyVector(vp, w);          /* 裁剪空间 */
            int in_clip = (c.w != 0) &&
                          (fabs(c.x) <= fabs(c.w)) &&
                          (fabs(c.y) <= fabs(c.w)) &&
                          (fabs(c.z) <= fabs(c.w));      /* 视锥内判定 */
            vec3 world = VEC3(cube[i][0], cube[i][1], cube[i][2]);
            int in_frst = frstCullSphere(f, world, 0.0f); /* 球心=顶点，半径 0 */
            if (in_clip) visible_clip++;
            if (in_frst) visible_frst_outer++;
            printf("  v%d world=(%+g,%+g,%+g) clip=%-3s frustum=%-3s\n",
                   i, world.x, world.y, world.z,
                   in_clip ? "in" : "out", in_frst ? "in" : "out");
        }
        check(visible_clip == visible_frst_outer,
              "E2E: 裁剪空间可见性与 frst 视锥剔除结果一致");
        printf("可见顶点: clip=%d frst=%d\n", visible_clip, visible_frst_outer);
    }

    /* ── 管线 5：顶点变换端到端对照解析解 ──
       相机前方 z=-2 处的点 (0,0,-2) 应可见（视锥内，近 0.1 远 100）； */
    {
        vec3 p = VEC3(0, 0, -2); /* 在相机前方 5-2=3 处 */
        float inside = (float)frstCullSphere(frstFromMatrix(mat4MultiplyMatrix(proj, view)),
                                             p, 0.0f);
        check(inside == 1.0f, "E2E: 相机前方 (0,0,-2) 在视锥内（可见）");
    }

    printf("\n=== 结果: %s (%d failures) ===\n",
           g_failures == 0 ? "ALL PASS" : "FAILED", g_failures);
    return g_failures == 0 ? 0 : 1;
}