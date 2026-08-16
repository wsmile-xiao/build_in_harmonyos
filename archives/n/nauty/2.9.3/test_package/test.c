/* 真实断言：用 nauty 算两个可手算图的自同构群阶。
 *
 *   K4（完全图，4 个顶点两两相连）  → |Aut| = 4! = 24
 *   P3（路径 0-1-2）                → |Aut| = 2（只有翻转）
 *
 * 这比 dlopen 探针硬得多：densenauty 是 nauty 的核心入口，算错/没算说明库根本没工作。
 * MAXN 必须在 include 之前定义（nauty 靠它决定用静态数组还是 DYNALLSTAT 动态分配）。
 */
#define MAXN 64
#include <stdio.h>
#include <nauty/nauty.h>

static long grporder(int n, const int edges[][2], int nedges)
{
    graph g[MAXN * MAXM];
    int lab[MAXN], ptn[MAXN], orbits[MAXN];
    static DEFAULTOPTIONS_GRAPH(options);
    statsblk stats;
    int m = SETWORDSNEEDED(n);
    int i;

    nauty_check(WORDSIZE, m, n, NAUTYVERSIONID);
    EMPTYGRAPH(g, m, n);
    for (i = 0; i < nedges; ++i)
        ADDONEEDGE(g, edges[i][0], edges[i][1], m);

    densenauty(g, lab, ptn, orbits, &options, &stats, m, n, NULL);
    /* 群阶 = grpsize1 × 10^grpsize2；这两个例子都小，grpsize2 恒为 0 */
    if (stats.grpsize2 != 0)
        return -1;
    return (long)(stats.grpsize1 + 0.5);
}

int main(void)
{
    static const int k4[][2] = {{0,1},{0,2},{0,3},{1,2},{1,3},{2,3}};
    static const int p3[][2] = {{0,1},{1,2}};
    long a = grporder(4, k4, 6);
    long b = grporder(3, p3, 2);
    int bad = 0;

    if (a != 24) { fprintf(stderr, "nauty: K4 的 |Aut| 应为 24，实得 %ld\n", a); bad = 1; }
    else printf("nauty: K4 |Aut| = %ld 通过\n", a);

    if (b != 2)  { fprintf(stderr, "nauty: P3 的 |Aut| 应为 2，实得 %ld\n", b); bad = 1; }
    else printf("nauty: P3 |Aut| = %ld 通过\n", b);

    return bad;
}
