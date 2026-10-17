/* test_package/test.cpp — bliss 0.77 consumer test
 *
 * 链接 libbliss 验证 C++ API：构造 Petersen 图（10 顶点 3-正则），
 * 计算其自同构群大小（Petersen 图的自同构群为 S5，大小 120），
 * 并验证规范标量可计算。
 */
#include <bliss/graph.hh>
#include <cstdio>
#include <cstdlib>

int main(void) {
    bliss::Graph g(10);
    /* Petersen 图：外圈 0-1-2-3-4-0，内圈五角星 5-7-9-6-8-5（步长 2），
     * 辐条 0-5,1-6,...。自同构群 = S5，大小 120。 */
    for (int i = 0; i < 5; i++) {
        g.add_edge(i, (i + 1) % 5);
        g.add_edge(5 + i, 5 + ((i + 2) % 5));
        g.add_edge(i, 5 + i);
    }

    bliss::Stats stats;
    const unsigned int * cl = g.canonical_form(stats, nullptr);
    if (!cl) {
        printf("[FAIL] canonical_form returned null\n");
        return 1;
    }
    /* Petersen 图自同构群大小 = 120（S5）；Stats 私有成员经公共 getter 读取 */
    long double grp = stats.get_group_size_approx();
    printf("[ok] bliss canonical labeling computed\n");
    printf("[ok] group size: %.0Lf (expect 120)\n", grp);
    printf("[ok] nodes: %lu, leaves: %lu, bad: %lu\n",
           stats.get_nof_nodes(),
           stats.get_nof_leaf_nodes(),
           stats.get_nof_bad_nodes());

    if (grp != 120.0L) {
        printf("[FAIL] group size mismatch: got %.0Lf, expect 120\n", grp);
        return 1;
    }
    printf("PASS: bliss 0.77 consumer test (Petersen automorphism group size = 120)\n");
    return 0;
}
