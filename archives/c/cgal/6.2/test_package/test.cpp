/* CGAL 6.2 真实功能断言。
 *
 * CGAL 6.x 是 header-only，没有 .so —— 这类包最容易退化成「能 #include 就算过」，
 * 而那测不出任何东西：头装全了、模板实例化不出来照样过不了下游。
 *
 * 故用**精确算术核**跑两个可手算的几何计算：
 *   ① 2D 凸包：给 6 个点，其中 2 个在内部，断言凸包恰好是外围 4 个点、且逆时针有序
 *   ② Delaunay 三角剖分：4 个点断言出 2 个三角形，并验点定位
 *
 * 选 Exact_predicates_exact_constructions_kernel 不是随意的：它在运行期**真的会调 GMP/MPFR**
 * 做任意精度有理数运算。这样一来，本测试同时验证了 gmp / mpfr 两个依赖确实接上了 ——
 * 若只用 inexact 的 double 核，即使 GMP 没链上也照样绿，等下游 pycgal 才炸。
 */
#include <CGAL/version.h>
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/convex_hull_2.h>
#include <CGAL/Delaunay_triangulation_2.h>
#include <cstdio>
#include <vector>

typedef CGAL::Exact_predicates_exact_constructions_kernel K;
typedef K::Point_2 Point;

static int test_convex_hull(void)
{
    /* 外围正方形 4 点 + 2 个严格在内部的点。凸包必须只剩那 4 个。 */
    std::vector<Point> pts = {
        Point(0, 0), Point(4, 0), Point(4, 4), Point(0, 4),   /* 外围 */
        Point(1, 1), Point(2, 3),                             /* 内部 */
    };
    std::vector<Point> hull;
    CGAL::convex_hull_2(pts.begin(), pts.end(), std::back_inserter(hull));

    if (hull.size() != 4) {
        std::printf("FAIL 凸包点数 %zu != 4（内部点没被剔除）\n", hull.size());
        return 1;
    }
    /* 面积必须是 16（4x4 正方形）。用叉积求多边形有向面积的两倍，
     * 逆时针为正 —— 同时验了输出顺序。 */
    K::FT twice_area = 0;
    for (size_t i = 0; i < hull.size(); i++) {
        const Point &a = hull[i], &b = hull[(i + 1) % hull.size()];
        twice_area += a.x() * b.y() - b.x() * a.y();
    }
    if (twice_area != 32) {
        std::printf("FAIL 凸包有向面积×2 = %s，期望 32（逆时针的 4x4 正方形）\n",
                    CGAL::to_double(twice_area) == 0 ? "0" : "非32");
        return 1;
    }
    std::printf("凸包 OK: 6 点 -> 4 点，有向面积×2 = 32（逆时针 4x4 正方形）\n");
    return 0;
}

static int test_delaunay(void)
{
    typedef CGAL::Delaunay_triangulation_2<K> DT;
    DT dt;
    dt.insert(Point(0, 0));
    dt.insert(Point(1, 0));
    dt.insert(Point(0, 1));
    dt.insert(Point(1, 1));

    if (dt.number_of_vertices() != 4) {
        std::printf("FAIL 顶点数 %zu != 4\n", (size_t)dt.number_of_vertices());
        return 1;
    }
    /* 单位正方形的 Delaunay 剖分恰好 2 个三角形 */
    if (dt.number_of_faces() != 2) {
        std::printf("FAIL 三角形数 %zu != 2\n", (size_t)dt.number_of_faces());
        return 1;
    }
    /* 点定位：正方形中心必须落在某个有限面里 */
    DT::Face_handle f = dt.locate(Point(K::FT(1) / 2, K::FT(1) / 3));
    if (f == nullptr || dt.is_infinite(f)) {
        std::printf("FAIL 中心点定位落到了无穷面\n");
        return 1;
    }
    std::printf("Delaunay OK: 4 顶点 -> 2 三角形，内点定位命中有限面\n");
    return 0;
}

int main(void)
{
    std::printf("CGAL 版本: %s (数值 %d)\n", CGAL_VERSION_STR, CGAL_VERSION_NR);
    if (CGAL_VERSION_NR < 1060200000) {
        std::printf("FAIL 版本号低于 6.2\n");
        return 1;
    }
    if (test_convex_hull()) return 1;
    if (test_delaunay())    return 1;
    std::printf("cgal 6.2: 全部断言通过\n");
    return 0;
}
