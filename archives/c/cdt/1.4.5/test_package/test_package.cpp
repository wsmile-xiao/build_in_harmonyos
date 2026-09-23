// cdt 1.4.5 — test_package 消费者验证
// 真实调用 CDT 公开 API：构建约束 Delaunay 三角剖分并校验拓扑（非空壳测试）
#include <CDT.h>
#include <VerifyTopology.h>

#include <cstdio>
#include <vector>

int main()
{
    using namespace CDT;

    // 简单四边形 + 一条对角线约束边
    const std::vector<V2d<double> > vertices = {
        {0.0, 0.0}, {1.0, 0.0}, {1.0, 1.0}, {0.0, 1.0},
    };
    const std::vector<Edge> edges = {
        Edge(VertInd(0), VertInd(2)),  // 对角线
    };

    Triangulation<double> cdt;
    cdt.insertVertices(vertices);
    cdt.insertEdges(edges);

    if(!verifyTopology(cdt))
    {
        std::fprintf(stderr, "FAIL: verifyTopology failed\n");
        return 1;
    }
    if(cdt.triangles.empty())
    {
        std::fprintf(stderr, "FAIL: no triangles generated\n");
        return 2;
    }

    cdt.eraseSuperTriangle();
    if(cdt.triangles.empty())
    {
        std::fprintf(stderr, "FAIL: empty after eraseSuperTriangle\n");
        return 3;
    }

    std::printf("cdt test_package: triangulation OK (%zu triangles, %zu vertices)\n",
                cdt.triangles.size(), cdt.vertices.size());
    return 0;
}
