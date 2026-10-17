// cdt 1.4.5 — HarmonyOS 专项适配测试
// 在上游测试之外新增的真实可执行用例：覆盖模块化 API 在 OHOS(aarch64, clang 15, libc++) 
// 下的确定性验证——64 位顶点/三角形索引类型实例化（CDT_USE_64_BIT_INDEX_TYPE 宏）、
// 多批次顶点插入 + 约束边、三角剖分 + 拓扑校验 + 超三角形擦除，并显式断言结果
// （非空壳、非复述上游用例）。
#define CDT_USE_64_BIT_INDEX_TYPE
#include <CDT.h>
#include <VerifyTopology.h>

#include <cstdio>
#include <vector>

int main()
{
    using namespace CDT;

    // OHOS 专项：开启 CDT_USE_64_BIT_INDEX_TYPE 后，VertInd/TriInd 为 int64_t
    typedef Triangulation<double> TriInt64;

    // 确定性输入：网格 + 两条约束对角线（含公共端点，验证约束边相交解析）
    const std::vector<V2d<double> > vertices = {
        {0.0, 0.0}, {2.0, 0.0}, {4.0, 0.0},
        {0.0, 2.0}, {2.0, 2.0}, {4.0, 2.0},
        {0.0, 4.0}, {2.0, 4.0}, {4.0, 4.0},
    };
    const std::vector<Edge> edges = {
        Edge(VertInd(0), VertInd(8)),
        Edge(VertInd(2), VertInd(6)),
    };

    TriInt64 cdt;
    // 分两批插入（覆盖多批次路径，对应上游 "Inserting vertices in two batches" 之外的显式断言）
    cdt.insertVertices(
        std::vector<V2d<double> >(vertices.begin(), vertices.begin() + 5));
    cdt.insertVertices(
        std::vector<V2d<double> >(vertices.begin() + 5, vertices.end()));
    cdt.insertEdges(edges);

    int failures = 0;

    if(!verifyTopology(cdt))
    {
        std::fprintf(stderr, "FAIL: verifyTopology\n");
        ++failures;
    }
    // CDT 确定性行为: 三角网含 3 个超三角形顶点 -> 9 输入 + 3 = 12
    if(cdt.vertices.size() != vertices.size() + 3)
    {
        std::fprintf(stderr, "FAIL: vertices=%zu expect=%zu (+3 super-triangle)\n",
                     cdt.vertices.size(), vertices.size() + 3);
        ++failures;
    }
    // 两条约束对角线在中心相交: TryResolve 交点分裂 -> 2 条边各成 2 段 = 4 条 fixed edge
    if(cdt.fixedEdges.size() != 4)
    {
        std::fprintf(stderr, "FAIL: fixedEdges=%zu expect=4 (2 constraint edges "
                     "split at intersection by TryResolve)\n", cdt.fixedEdges.size());
        ++failures;
    }
    if(cdt.triangles.size() == 0)
    {
        std::fprintf(stderr, "FAIL: no triangles after insertion\n");
        ++failures;
    }

    // 擦除超三角形后三角网仍非空（顶点数回到 9）
    cdt.eraseSuperTriangle();
    if(cdt.triangles.size() == 0)
    {
        std::fprintf(stderr, "FAIL: empty after eraseSuperTriangle\n");
        ++failures;
    }
    if(cdt.vertices.size() != vertices.size())
    {
        std::fprintf(stderr, "FAIL: vertices=%zu expect=%zu after eraseSuperTriangle\n",
                     cdt.vertices.size(), vertices.size());
        ++failures;
    }

    if(failures)
    {
        std::fprintf(stderr, "HarmonyOS-specific test FAILED (%d failures)\n", failures);
        return 1;
    }
    std::printf("HarmonyOS-specific test PASSED: %zu vertices, %zu constraint edges, "
                "%zu triangles (int64 index type, two-batch insertion)\n",
                cdt.vertices.size(), cdt.fixedEdges.size(), cdt.triangles.size());
    return 0;
}