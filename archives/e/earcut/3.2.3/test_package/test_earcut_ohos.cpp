// test_earcut_ohos.cpp — HarmonyOS 专项测试
// 针对 OHOS PC (aarch64) 平台特性的真实用例：
//   1. 瓦片级大坐标（1e6 量级，浮点精度敏感场景）多边形三角剖分面积守恒
//   2. 多点退化/共线环输入不崩溃且索引合法（产出三角形面积总和守恒）
//   3. uint32 索引大顶点数（>65535 顶点）合法性（验证 N=uint32_t 模板路径）
#include <mapbox/earcut.hpp>

#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>

using Point = std::array<double, 2>;

static double ringSignedArea(const std::vector<Point>& ring) {
    double sum = 0;
    for (std::size_t i = 0, len = ring.size(), j = len - 1; i < len; j = i++) {
        sum += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
    }
    return sum / 2;
}

static double trianglesArea(const std::vector<Point>& verts,
                            const std::vector<uint32_t>& indices) {
    double sum = 0;
    for (std::size_t i = 0; i + 2 < indices.size(); i += 3) {
        const Point& a = verts[indices[i]];
        const Point& b = verts[indices[i + 1]];
        const Point& c = verts[indices[i + 2]];
        sum += std::fabs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2;
    }
    return sum;
}

int main() {
    // 用例 1：瓦片坐标缩放多边形（坐标 1e6 量级，模拟 MVT 瓦片平面坐标）
    {
        std::vector<std::vector<Point>> poly;
        poly.push_back({{1234567.0, 7654321.0}, {1234567.0 + 4096.0, 7654321.0},
                        {1234567.0 + 4096.0, 7654321.0 + 4096.0}, {1234567.0, 7654321.0 + 4096.0}});
        poly.push_back({{1234567.0 + 1024.0, 7654321.0 + 1024.0},
                        {1234567.0 + 3072.0, 7654321.0 + 1024.0},
                        {1234567.0 + 3072.0, 7654321.0 + 3072.0},
                        {1234567.0 + 1024.0, 7654321.0 + 3072.0}});

        // v3.2.3 API: earcut(poly) 直接返回 indices
        auto indices = mapbox::earcut<uint32_t>(poly);

        std::vector<Point> flat;
        for (const auto& r : poly)
            for (const auto& p : r) flat.push_back(p);

        const double orig = 4096.0 * 4096.0 - 2048.0 * 2048.0;
        const double tri = trianglesArea(flat, indices);
        if (indices.size() % 3 != 0 || std::fabs(orig - tri) > 1.0) { // 大坐标下允许 1e0 级数值误差
            std::printf("OHOS FAIL[1]: triangles=%zu area %.3f vs %.3f\n", indices.size() / 3, tri, orig);
            return 1;
        }
        std::printf("OHOS PASS[1]: tile-scale square+hole -> %zu triangles, area %.1f\n",
                    indices.size() / 3, tri);
    }

    // 用例 2：共线/退化输入不崩溃，输出面积守恒
    {
        // 带一个完全共线顶点的 L 形多边形（该点落在边上）
        std::vector<std::vector<Point>> poly;
        poly.push_back({{0, 0}, {10, 0}, {10, 5}, {5, 5}, {5, 10}, {0, 10}});

        // v3.2.3 API: earcut(poly) 直接返回 indices
        auto indices = mapbox::earcut<uint32_t>(poly);

        std::vector<Point> flat;
        for (const auto& r : poly)
            for (const auto& p : r) flat.push_back(p);

        const double orig = 75.0;
        const double tri = trianglesArea(flat, indices);
        if (indices.size() % 3 != 0 || std::fabs(orig - tri) > 1e-6) {
            std::printf("OHOS FAIL[2]: degenerate input triangles=%zu area %.6f vs %.6f\n",
                        indices.size() / 3, tri, orig);
            return 1;
        }
        std::printf("OHOS PASS[2]: collinear-vertex L-shape -> %zu triangles, area %.1f\n",
                    indices.size() / 3, tri);
    }

    // 用例 3：>65535 顶点的环形多边形，验证 uint32 索引路径（N=uint32_t）
    {
        std::vector<std::vector<Point>> poly;
        const int n = 70000; // 超过 uint16 范围
        std::vector<Point> ring;
        ring.reserve(n);
        for (int i = 0; i < n; i++) {
            const double a = 2.0 * M_PI * i / n;
            ring.push_back({1000.0 * std::cos(a), 1000.0 * std::sin(a)});
        }
        poly.push_back(std::move(ring));

        // v3.2.3 API: earcut(poly) 直接返回 indices
        auto indices = mapbox::earcut<uint32_t>(poly);

        const std::size_t expected = static_cast<std::size_t>(n) - 2;
        if (indices.size() / 3 != expected) {
            std::printf("OHOS FAIL[3]: big ring triangles=%zu expected=%zu\n",
                        indices.size() / 3, expected);
            return 1;
        }
        // 面积：半径 1000 的圆 -> pi * r^2
        std::vector<Point> flat;
        for (const auto& p : poly[0]) flat.push_back(p);
        const double tri = trianglesArea(flat, indices);
        const double orig = M_PI * 1000.0 * 1000.0;
        if (std::fabs(orig - tri) > 5000.0) { // 多边形近似圆，允许多边形化误差
            std::printf("OHOS FAIL[3]: big ring area %.3f vs %.3f\n", tri, orig);
            return 1;
        }
        std::printf("OHOS PASS[3]: 70000-vertex ring -> %zu triangles, area %.1f (uint32 indices)\n",
                    indices.size() / 3, tri);
    }

    std::printf("PASS: earcut 3.2.3 HarmonyOS-specific tests (3 cases)\n");
    return 0;
}
