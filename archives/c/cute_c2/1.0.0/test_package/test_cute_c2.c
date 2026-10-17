/*
 * test_cute_c2.c — 真实 2D 碰撞 API 冒烟测试（鸿蒙平台消费者视角）。
 *
 * cute_c2 1.0.0 对应上游 tinyc2.h v1.0，其实现宏为 TINYC2_IMPL
 * （CUTE_C2_IMPLEMENTATION 为改名后 master 版本的宏）。
 *   1. c2CircletoCircle: 相交圆 → 非 0；分离圆 → 0
 *   2. c2AABBtoAABB:    相交 AABB → 非 0；分离 AABB → 0
 *   3. c2MakePoly + c2PolytoPoly: 相交凸多边形 → 非 0
 *   4. c2Collide 生成 manifold: 相交时 count>0
 *   5. c2CastRay / c2RaytoAABB: 射线命中 → 非 0
 * 全部通过打印 HMBS_TEST_PACKAGE_RESULT: PASS。
 */
#include <stdio.h>

#define TINYC2_IMPL
#include "cute_c2.h"

static int g_failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (cond) {                                                         \
            printf("  [PASS] %s\n", msg);                                   \
        } else {                                                            \
            printf("  [FAIL] %s\n", msg);                                   \
            g_failures++;                                                   \
        }                                                                   \
    } while (0)

int main(void)
{
    printf("cute_c2 test_package smoke\n");

    /* 1. circle-circle */
    c2Circle a = { { 100.f, 100.f }, 10.f };
    c2Circle b = { { 105.f, 100.f }, 10.f };
    c2Circle c = { { 200.f, 200.f }, 10.f };
    CHECK(c2CircletoCircle(a, b) != 0, "overlapping circles hit");
    CHECK(c2CircletoCircle(a, c) == 0, "separated circles miss");

    /* 2. AABB-AABB */
    c2AABB aa = { { 0.f, 0.f }, { 10.f, 10.f } };
    c2AABB bb = { { 5.f, 5.f }, { 15.f, 15.f } };
    c2AABB cc = { { 50.f, 50.f }, { 60.f, 60.f } };
    CHECK(c2AABBtoAABB(aa, bb) != 0, "overlapping AABBs hit");
    CHECK(c2AABBtoAABB(aa, cc) == 0, "separated AABBs miss");

    /* 3. polygon-polygon via convex hull (v1.0: fill verts/count then c2MakePoly) */
    {
        c2Poly p, q;
        p.count = 4;
        p.verts[0] = c2V(0.f, 0.f);
        p.verts[1] = c2V(10.f, 0.f);
        p.verts[2] = c2V(10.f, 10.f);
        p.verts[3] = c2V(0.f, 10.f);
        q.count = 4;
        q.verts[0] = c2V(5.f, 5.f);
        q.verts[1] = c2V(15.f, 5.f);
        q.verts[2] = c2V(15.f, 15.f);
        q.verts[3] = c2V(5.f, 15.f);
        c2MakePoly(&p);
        c2MakePoly(&q);
        CHECK(c2PolytoPoly(&p, NULL, &q, NULL) != 0, "overlapping polys hit");
    }

    /* 4. manifold */
    {
        c2Manifold m;
        c2CircletoCircleManifold(a, b, &m);
        CHECK(m.count == 1, "manifold count == 1 for overlapping circles");
    }

    /* 5. ray cast onto AABB */
    {
        c2Ray r = { { -5.f, 5.f }, { 1.f, 0.f }, 100.f };
        c2Raycast ray;
        CHECK(c2RaytoAABB(r, aa, &ray) != 0, "ray hits AABB");
    }

    if (g_failures == 0) {
        printf("HMBS_TEST_PACKAGE_RESULT: PASS (5 checks)\n");
        return 0;
    }
    printf("HMBS_TEST_PACKAGE_RESULT: FAIL (%d checks)\n", g_failures);
    return 1;
}