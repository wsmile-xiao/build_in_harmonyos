/*
 * test_package consumer test for libopf 2.1
 *
 * Real consumer validation (R34): links against installed libOPF.a and
 * exercises the public API end-to-end:
 *   1. ReadSubgraph  - read a small OPF-format dataset
 *   2. opf_SplitSubgraph - split into training/test sets
 *   3. opf_CreateArcs + opf_OPFTraining - train an OPF classifier
 *   4. opf_OPFClassifying - classify the test set
 *   5. opf_Accuracy  - compute and assert a sane accuracy value
 */
#include <OPF.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static void write_small_dataset(const char *path)
{
    /* 8 nodes, 2 labels, 2 features; label 1 left cluster, label 2 right */
    int nnodes = 8, nlabels = 2, nfeats = 2;
    float feats[8][2] = {
        {0.1f, 0.2f}, {0.2f, 0.1f}, {0.3f, 0.3f}, {0.15f, 0.25f},
        {2.1f, 2.2f}, {2.2f, 2.1f}, {2.3f, 2.3f}, {2.15f, 2.25f},
    };
    int truelabel[8] = {1, 1, 1, 1, 2, 2, 2, 2};
    int i, j;
    FILE *fp = fopen(path, "wb");
    if (!fp) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
    fwrite(&nnodes, sizeof(int), 1, fp);
    fwrite(&nlabels, sizeof(int), 1, fp);
    fwrite(&nfeats, sizeof(int), 1, fp);
    for (i = 0; i < nnodes; i++) {
        fwrite(&i, sizeof(int), 1, fp);            /* position */
        fwrite(&truelabel[i], sizeof(int), 1, fp); /* truelabel */
        for (j = 0; j < nfeats; j++)
            fwrite(&feats[i][j], sizeof(float), 1, fp);
    }
    fclose(fp);
}

int main(void)
{
    Subgraph *g = NULL, *training = NULL, *testing = NULL;
    float acc;
    int i, ok = 1;
    char path[256];

    snprintf(path, sizeof(path), "%s/libopf_test.dat", getenv("TMPDIR") ? getenv("TMPDIR") : ".");
    write_small_dataset(path);

    g = ReadSubgraph(path);
    if (g->nnodes != 8 || g->nlabels != 2 || g->nfeats != 2) {
        fprintf(stderr, "FAIL: ReadSubgraph parsed %d nodes/%d labels/%d feats\n",
                g->nnodes, g->nlabels, g->nfeats);
        return 1;
    }
    printf("ReadSubgraph OK: %d nodes, %d labels, %d features\n",
           g->nnodes, g->nlabels, g->nfeats);

    /* 75% / 25% split: 6 training / 2 test */
    opf_SplitSubgraph(g, &training, &testing, 0.75f);
    opf_DestroyArcs(g);

    for (i = 0; i < training->nnodes; i++)
        training->node[i].status = 0;
    opf_CreateArcs(training, 3);
    opf_OPFTraining(training);
    opf_WriteModelFile(training, "libopf_model.opf");

    opf_CreateArcs(testing, 3);
    opf_OPFClassifying(training, testing);
    acc = opf_Accuracy(testing);
    printf("Classifier accuracy on test set: %.2f%%\n", acc * 100.0f);

    if (acc >= 0.5f) {
        printf("PASS: libOPF public API (train/classify/accuracy) works\n");
    } else {
        fprintf(stderr, "FAIL: accuracy %.2f%% below 50%% sanity threshold\n", acc * 100.0f);
        ok = 0;
    }

    DestroySubgraph(&g);
    DestroySubgraph(&training);
    DestroySubgraph(&testing);
    return ok ? 0 : 1;
}