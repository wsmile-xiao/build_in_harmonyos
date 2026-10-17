/*
 * test_planarity.c — test_package 消费者测试（鸿蒙特有）
 *
 * 目的：在 HarmonyOS PC(aarch64) 上以「下游消费者」身份真实调用 libplanarity
 * 公共 API（<planarity/graphLib.h>），验证图解析、图构造、平面性判定、
 * 平面/外平面嵌入、Kuratowski 障碍子图隔离、嵌入完整性校验与图序列化。
 *
 * API 语义（实测确认，见 reports/ 与 PR 说明）：
 *   - 顶点索引为 **1-based**（1..N）；顶点 0 是 NIL，不是有效顶点。
 *     邻接表文件里的 "0:" 仍是 0-based 文本表示（flags 置 GRAPHFLAGS_ZEROBASEDIO=16），
 *     但入内存后的公共图 API 一律用 1..N。
 *   - gp_IsNeighbor() 返回 TRUE/FALSE；gp_FindEdge() 返回边号而不是布尔。
 *   - gp_Embed() 返回 OK(1) / NONEMBEDDABLE(-1) / NOTOK(0)。
 *   - gp_TestEmbedResultIntegrity() 在成功路径上返回与 embedResult **相同**的值
 *     （OK 或 NONEMBEDDABLE），出错才返回 NOTOK；因此校验写成 integrity == embedResult。
 *
 * 断言口径：每个 CHECK() 计 1 条断言；末尾输出 "ASSERTIONS: PASS/TOTAL"。
 * 退出码：0 = 全部通过，1 = 存在失败断言。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <planarity/graphLib.h>

static int g_total = 0;
static int g_failed = 0;

static void check(int cond, const char *msg)
{
    g_total++;
    if (cond) {
        printf("  [PASS] %s\n", msg);
    } else {
        printf("  [FAIL] %s\n", msg);
        g_failed++;
    }
}

/* K4（平面图，邻接表文本；文本索引 0-based，入内存后为 1..4） */
static char K4[] = "N=4\n0: 1 2 3 -1\n1: 0 2 3 -1\n2: 0 1 3 -1\n3: 0 1 2 -1\n";
/* K3,3（非平面完全二部图） */
static char K33[] = "N=6\n0: 3 4 5 -1\n1: 3 4 5 -1\n2: 3 4 5 -1\n3: 0 1 2 -1\n4: 0 1 2 -1\n5: 0 1 2 -1\n";
/* C4（外平面图） */
static char C4[] = "N=4\n0: 1 3 -1\n1: 0 2 -1\n2: 1 3 -1\n3: 0 2 -1\n";

int main(void)
{
    graphP g = NULL;
    graphP orig = NULL;
    char *outStr = NULL;
    int result = 0;
    int integrity = 0;

    printf("== libplanarity 消费者测试（HarmonyOS PC aarch64）==\n");

    /* ---------- 1. 图解析 + 序列化（K4） ---------- */
    printf("[1] K4：解析邻接表 → 顶点/边/邻接查询 → 回写\n");
    g = gp_New();
    check(g != NULL, "gp_New() 返回非空图对象");
    if (g == NULL)
        return 1;

    check(gp_ReadFromString(g, K4) == OK, "gp_ReadFromString(K4) == OK");
    check(gp_GetN(g) == 4, "gp_GetN(K4) == 4");
    check(gp_GetM(g) == 6, "gp_GetM(K4) == 6");
    check(gp_GetVertexDegree(g, 1) == 3, "gp_GetVertexDegree(K4, 1) == 3（1-based 顶点 1）");
    check(gp_GetVertexDegree(g, 4) == 3, "gp_GetVertexDegree(K4, 4) == 3");
    check(gp_IsNeighbor(g, 1, 2) == TRUE, "gp_IsNeighbor(K4, 1, 2) 为真");
    check(gp_IsNeighbor(g, 2, 3) == TRUE, "gp_IsNeighbor(K4, 2, 3) 为真");
    check(gp_IsNeighbor(g, 1, 1) == FALSE, "gp_IsNeighbor(K4, 1, 1) 为假（无自环）");
    check(gp_FindEdge(g, 1, 2) > 0, "gp_FindEdge(K4, 1, 2) 返回正边号");

    outStr = NULL;
    check(gp_WriteToString(g, &outStr, WRITE_ADJLIST) == OK,
          "gp_WriteToString(WRITE_ADJLIST) == OK");
    check(outStr != NULL && strstr(outStr, "N=4") != NULL,
          "邻接表回写含顶点数 N=4");
    if (outStr != NULL) {
        free(outStr);
        outStr = NULL;
    }

    orig = gp_DupGraph(g);
    check(orig != NULL, "gp_DupGraph(K4) 返回非空副本");
    result = gp_Embed(g, EMBEDFLAGS_PLANAR);
    check(result == OK, "K4 gp_Embed(EMBEDFLAGS_PLANAR) == OK（可平面）");
    integrity = gp_TestEmbedResultIntegrity(g, orig, result);
    check(integrity == result, "K4 嵌入结果完整性校验返回 OK");
    gp_Free(&orig);
    gp_Free(&g);

    /* ---------- 2. 非平面障碍子图隔离（K3,3） ---------- */
    printf("[2] K3,3：非平面判定 + Kuratowski 障碍子图隔离\n");
    g = gp_New();
    check(g != NULL, "gp_New()（K3,3）返回非空图对象");
    check(gp_ReadFromString(g, K33) == OK, "gp_ReadFromString(K33) == OK");
    check(gp_GetN(g) == 6, "K33 顶点数 N == 6");
    check(gp_GetM(g) == 9, "K33 边数 M == 9");

    orig = gp_DupGraph(g);
    check(orig != NULL, "gp_DupGraph(K33) 返回非空副本");
    result = gp_Embed(g, EMBEDFLAGS_PLANAR);
    check(result == NONEMBEDDABLE, "K33 gp_Embed(PLANAR) == NONEMBEDDABLE（非平面）");
    check(gp_GetObstructionMinorType(g) != MINORTYPE_NONE,
          "K33 隔离出的障碍子图类型非 NONE");
    check((gp_GetObstructionMinorType(g) & MINORTYPE_A) != 0,
          "K33 障碍子图类型含 MINORTYPE_A（K3,3 型）");
    integrity = gp_TestEmbedResultIntegrity(g, orig, result);
    check(integrity == result, "K33 障碍子图完整性校验返回 NONEMBEDDABLE");
    gp_Free(&orig);
    gp_Free(&g);

    /* ---------- 3. 程序化构图 + 外平面嵌入（C4） ---------- */
    printf("[3] C4：gp_AddEdge 程序化构图 → 外平面嵌入\n");
    g = gp_New();
    check(g != NULL, "gp_New()（C4）返回非空图对象");
    check(gp_EnsureVertexCapacity(g, 4) == OK, "gp_EnsureVertexCapacity(C4, 4) == OK");
    check(gp_EnsureEdgeCapacity(g, 4) == OK, "gp_EnsureEdgeCapacity(C4, 4) == OK");
    g->N = 4;
    check(gp_AddEdge(g, 1, 0, 2, 0) == OK, "gp_AddEdge(C4, 1-2) == OK");
    check(gp_AddEdge(g, 2, 0, 3, 0) == OK, "gp_AddEdge(C4, 2-3) == OK");
    check(gp_AddEdge(g, 3, 0, 4, 0) == OK, "gp_AddEdge(C4, 3-4) == OK");
    check(gp_AddEdge(g, 4, 0, 1, 0) == OK, "gp_AddEdge(C4, 4-1) == OK");
    check(gp_GetM(g) == 4, "C4 由 gp_AddEdge 构造后 M == 4");
    check(gp_GetVertexDegree(g, 1) == 2, "C4 顶点 1 度数为 2");

    orig = gp_DupGraph(g);
    result = gp_Embed(g, EMBEDFLAGS_OUTERPLANAR);
    check(result == OK, "C4 gp_Embed(EMBEDFLAGS_OUTERPLANAR) == OK（可外平面）");
    integrity = gp_TestEmbedResultIntegrity(g, orig, result);
    check(integrity == result, "C4 外平面嵌入完整性校验返回 OK");
    gp_Free(&orig);
    gp_Free(&g);

    /* ---------- 4. 平面图的外平面性对照（K4 非外平面） ---------- */
    printf("[4] K4：外平面性对照（K4 非外平面）\n");
    g = gp_New();
    check(gp_ReadFromString(g, K4) == OK, "gp_ReadFromString(K4)（外平面轮）== OK");
    orig = gp_DupGraph(g);
    result = gp_Embed(g, EMBEDFLAGS_OUTERPLANAR);
    check(result == NONEMBEDDABLE, "K4 gp_Embed(OUTERPLANAR) == NONEMBEDDABLE（非外平面）");
    check(gp_GetObstructionMinorType(g) != MINORTYPE_NONE,
          "K4 外平面障碍子图类型非 NONE");
    integrity = gp_TestEmbedResultIntegrity(g, orig, result);
    check(integrity == result, "K4 外平面障碍子图完整性校验返回 NONEMBEDDABLE");
    gp_Free(&orig);
    gp_Free(&g);

    /* ---------- 5. 平面嵌入的另一条算法路径（C4） ---------- */
    printf("[5] C4：平面嵌入（同一图不同算法路径）\n");
    g = gp_New();
    check(gp_ReadFromString(g, C4) == OK, "gp_ReadFromString(C4) == OK");
    orig = gp_DupGraph(g);
    result = gp_Embed(g, EMBEDFLAGS_PLANAR);
    check(result == OK, "C4 gp_Embed(EMBEDFLAGS_PLANAR) == OK");
    integrity = gp_TestEmbedResultIntegrity(g, orig, result);
    check(integrity == result, "C4 平面嵌入完整性校验返回 OK");
    gp_Free(&orig);
    gp_Free(&g);

    printf("ASSERTIONS: %d/%d\n", g_total - g_failed, g_total);
    if (g_failed != 0) {
        printf("FAILED assertions: %d\n", g_failed);
        return 1;
    }
    printf("ALL ASSERTIONS PASSED\n");
    return 0;
}
