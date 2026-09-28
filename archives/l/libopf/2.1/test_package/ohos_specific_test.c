/*
 * ohos_specific_test.c — HarmonyOS 平台专项测试 (libopf 2.1)
 *
 * 验证两个 aarch64/OHOS 平台适配修复点：
 *   1. opf_SplitSubgraph 不再因 SNode.status 无符号 char 与 NIL(-1) 比较失效
 *      而段错误（修复 1：subgraph.h 中 status/relevant 改为 signed char）。
 *   2. opf_ConfusionMatrix / opf_Accuracy 在聚类 label 超过 nlabels 时
 *      不再堆越界（修复 2：OPF.c 按最大 label 扩容矩阵）。
 *
 * 编译：clang -I<include> -I<include/util> ohos_specific_test.c -lOPF -lm
 */
#include <OPF.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void write_dataset(const char *path, int nnodes, int nlabels, int nfeats,
                          float feats[][2], int *truelabel)
{
    int i, j;
    FILE *fp = fopen(path, "wb");
    if (!fp) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
    fwrite(&nnodes, sizeof(int), 1, fp);
    fwrite(&nlabels, sizeof(int), 1, fp);
    fwrite(&nfeats, sizeof(int), 1, fp);
    for (i = 0; i < nnodes; i++) {
        fwrite(&i, sizeof(int), 1, fp);
        fwrite(&truelabel[i], sizeof(int), 1, fp);
        for (j = 0; j < nfeats; j++)
            fwrite(&feats[i][j], sizeof(float), 1, fp);
    }
    fclose(fp);
}

static int test_split_subgraph(void)
{
    /* 8 nodes, 2 labels, 2 feats; label 1 left, label 2 right */
    float feats[8][2] = {
        {0.1f, 0.2f}, {0.2f, 0.1f}, {0.3f, 0.3f}, {0.15f, 0.25f},
        {2.1f, 2.2f}, {2.2f, 2.1f}, {2.3f, 2.3f}, {2.15f, 2.25f},
    };
    int tl[8] = {1, 1, 1, 1, 2, 2, 2, 2};
    Subgraph *g = NULL, *sg1 = NULL, *sg2 = NULL;
    char path[256];
    int rc = 1;

    snprintf(path, sizeof(path), "%s/ohos_split.dat", getenv("TMPDIR") ? getenv("TMPDIR") : ".");
    write_dataset(path, 8, 2, 2, feats, tl);

    g = ReadSubgraph(path);
    if (!g || g->nnodes != 8) { fprintf(stderr, "FAIL: ReadSubgraph\n"); goto out; }

    /* 75%/25% split — must not crash (signed char NIL fix) */
    opf_SplitSubgraph(g, &sg1, &sg2, 0.75f);
    if (sg1->nnodes + sg2->nnodes != 8) {
        fprintf(stderr, "FAIL: split sizes %d+%d != 8\n", sg1->nnodes, sg2->nnodes);
        goto out;
    }
    if (sg1->nnodes != 6 || sg2->nnodes != 2) {
        /* 随机采样分割，允许 ±1 浮动（向上取整） */
        fprintf(stderr, "WARN: split sizes %d+%d (expect ~6+2)\n", sg1->nnodes, sg2->nnodes);
    }
    printf("PASS[1] opf_SplitSubgraph: %d+%d=%d nodes, no crash\n",
           sg1->nnodes, sg2->nnodes, sg1->nnodes + sg2->nnodes);
    rc = 0;
out:
    if (sg1) DestroySubgraph(&sg1);
    if (sg2) DestroySubgraph(&sg2);
    if (g) DestroySubgraph(&g);
    return rc;
}

static int test_cluster_label_overflow(void)
{
    /* 4 nodes, 2 labels; manually assign cluster labels (3 > nlabels==2)
       to trigger the overflow path of opf_ConfusionMatrix/opf_Accuracy */
    float feats[4][2] = {
        {0.1f, 0.2f}, {0.2f, 0.1f}, {2.1f, 2.2f}, {2.2f, 2.1f},
    };
    int tl[4] = {1, 1, 2, 2};
    Subgraph *g = NULL;
    char path[256];
    int rc = 1, i;
    int **cm = NULL;

    snprintf(path, sizeof(path), "%s/ohos_cluster.dat", getenv("TMPDIR") ? getenv("TMPDIR") : ".");
    write_dataset(path, 4, 2, 2, feats, tl);

    g = ReadSubgraph(path);
    if (!g || g->nnodes != 4) { fprintf(stderr, "FAIL: ReadSubgraph\n"); goto out; }

    /* simulate clustering output: labels 3 (max > nlabels==2) */
    g->node[2].label = 3;
    g->node[3].label = 3;

    cm = opf_ConfusionMatrix(g);          /* must not overflow */
    {
        float acc = opf_Accuracy(g);      /* must not overflow */
        if (acc != acc || acc < 0.0f || acc > 1.0f) {
            fprintf(stderr, "FAIL: opf_Accuracy returned %f (expect 0..1)\n", acc);
            goto out;
        }
        printf("PASS[2] opf_ConfusionMatrix/opf_Accuracy with label>nlabels: acc=%.2f%%\n",
               acc * 100.0f);
    }

    for (i = 0; i < g->nlabels + 1; i++) free(cm[i]);
    free(cm);
    rc = 0;
out:
    if (g) DestroySubgraph(&g);
    return rc;
}

int main(void)
{
    int rc = 0;
    printf("=== libopf OHOS platform-specific test ===\n");
    printf("arch check: signed char = %s\n", (char)-1 < 0 ? "signed" : "UNSIGNED");
    rc |= test_split_subgraph();
    rc |= test_cluster_label_overflow();
    if (rc == 0)
        printf("ALL OHOS SPECIFIC TESTS PASSED\n");
    return rc;
}
