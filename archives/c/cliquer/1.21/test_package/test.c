/* cliquer test_package —— 真实计算 + 数值断言
 *
 * 断言依据（可手算）：
 *   K4（顶点 0..3 两两相连）+ 孤立顶点 4  →  最大团 = 4
 *   删掉边 (0,1) 之后                      →  最大团 = 3（0..3 不再是完全图，
 *                                             但 {1,2,3} 与 {0,2,3} 仍是三角形）
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <cliquer/cliquer.h>

int main(void) {
    int i, j, got;

    graph_t *g = graph_new(5);
    if (g == NULL) {
        fprintf(stderr, "cliquer: graph_new(5) 返回 NULL\n");
        return 1;
    }
    for (i = 0; i < 4; i++)
        for (j = i + 1; j < 4; j++)
            GRAPH_ADD_EDGE(g, i, j);

    got = clique_unweighted_max_weight(g, clique_default_options);
    printf("cliquer: K4+孤立点 最大团 = %d（期望 4）\n", got);
    if (got != 4) {
        fprintf(stderr, "cliquer: FAIL —— 期望 4，实得 %d\n", got);
        graph_free(g);
        return 1;
    }

    GRAPH_DEL_EDGE(g, 0, 1);
    got = clique_unweighted_max_weight(g, clique_default_options);
    printf("cliquer: 删边(0,1) 后最大团 = %d（期望 3）\n", got);
    if (got != 3) {
        fprintf(stderr, "cliquer: FAIL —— 期望 3，实得 %d\n", got);
        graph_free(g);
        return 1;
    }

    graph_free(g);
    printf("cliquer: OK —— 真实计算断言通过\n");
    return 0;
}
