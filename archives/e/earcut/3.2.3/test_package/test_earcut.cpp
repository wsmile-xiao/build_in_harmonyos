// test_earcut.cpp — L1 消费者冒烟测试（R34：真实调用被测包 API）
// 验证 include/mapbox/earcut.hpp 可正常包含、方形+洞多边形三角剖分正确：
//   - 索引数组长度 == 三角形数*3
//   - 三角剖分面积守恒（与原多边形面积一致）
#include <mapbox/earcut.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <vector>

using Point = std::array<double, 2>;

static double polygonArea(const std::vector<std::vector<Point>>& polygon) {
    // 首环为外环（取绝对值），其余环为孔（减去其面积），与 earcut 的孔洞语义一致
    double sum = 0;
    bool first = true;
    for (const auto& ring : polygon) {
        double ringSum = 0;
        for (std::size_t i = 0, len = ring.size(), j = len - 1; i < len; j = i++) {
            ringSum += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
        }
        if (first) {
            sum += std::fabs(ringSum) / 2;
            first = false;
        } else {
            sum -= std::fabs(ringSum) / 2;
        }
    }
    return sum;
}

static double trianglesArea(const std::vector<Point>& verts,
                            const std::vector<uint32_t>& indices) {
    double sum = 0;
    for (std::size_t i = 0; i < indices.size(); i += 3) {
        const Point& a = verts[indices[i]];
        const Point& b = verts[indices[i + 1]];
        const Point& c = verts[indices[i + 2]];
        sum += std::fabs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2;
    }
    return sum;
}

int main() {
    // 外环：10x10 方形；内环：2x2 洞（逆时针外环/顺时针内环约定由 earcut 自动处理）
    std::vector<std::vector<Point>> polygon;
    polygon.push_back({{0, 0}, {10, 0}, {10, 10}, {0, 10}});
    polygon.push_back({{3, 3}, {7, 3}, {7, 7}, {3, 7}});

    // v3.2.3 API: earcut(poly) 直接返回 std::vector<uint32_t> indices
    auto indices = mapbox::earcut<uint32_t>(polygon);

    // 顶点数 n=8（外4+内4），带洞多边形三角剖分三角形数 = n + 2*h - 2 = 8 + 2*1 - 2 = 8
    const std::size_t n = 8, h = 1;
    const std::size_t triCount = n + 2 * h - 2;

    if (indices.size() % 3 != 0 || indices.size() / 3 != triCount) {
        std::printf("FAIL: indices=%zu, expected triangles=%zu\n", indices.size() / 3, triCount);
        return 1;
    }

    // 展平顶点用于面积计算
    std::vector<Point> flat;
    for (const auto& ring : polygon)
        for (const auto& p : ring) flat.push_back(p);

    const double orig = polygonArea(polygon);   // 100 - 16 = 84
    const double tri = trianglesArea(flat, indices);
    if (std::fabs(orig - tri) > 1e-9) {
        std::printf("FAIL: area orig=%.9f triangles=%.9f\n", orig, tri);
        return 1;
    }

    std::printf("PASS: earcut 3.2.3 consumer smoke — %zu triangles, area %.3f == %.3f\n",
                indices.size() / 3, orig, tri);
    return 0;
}
