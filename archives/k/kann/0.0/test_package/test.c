#include <stdio.h>
#include <stdlib.h>
#include "kann.h"

int main(void) {
    int i, k, mask = (1<<8)-1, n_err = 0, max_k;
    float **x, **y, max, *x1;
    kad_node_t *t;
    kann_t *ann;
    int n = 400;

    /* 通过公开 API 构造 8->16(ReLU)->8(CEM) MLP */
    t = kann_layer_input(8);
    t = kad_relu(kann_layer_linear(t, 16));
    t = kann_layer_cost(t, 8, KANN_C_CEM);
    ann = kann_new(t, 0);
    if (ann == NULL) { fprintf(stderr, "kann_new failed\n"); return 1; }

    /* 训练数据：popcount */
    x = (float**)calloc(n, sizeof(float*));
    y = (float**)calloc(n, sizeof(float*));
    for (i = 0; i < n; ++i) {
        int c, a = rand() & (mask>>1);
        x[i] = (float*)calloc(8, sizeof(float));
        y[i] = (float*)calloc(8, sizeof(float));
        for (k = c = 0; k < 8; ++k)
            x[i][k] = (float)(a>>k&1), c += (a>>k&1);
        y[i][c] = 1.0f;
    }
    kann_train_fnn1(ann, 0.1f, 32, 15, 10, 0.1f, n, x, y);

    /* 预测验证 */
    x1 = (float*)calloc(8, sizeof(float));
    for (i = 0; i < 200; ++i) {
        int c, a = rand() & (mask>>1);
        const float *y1;
        for (k = c = 0; k < 8; ++k)
            x1[k] = (float)(a>>k&1), c += (a>>k&1);
        y1 = kann_apply1(ann, x1);
        for (k = 0, max_k = -1, max = -1.0f; k < 8; ++k)
            if (max < y1[k]) max = y1[k], max_k = k;
        if (max_k != c) ++n_err;
    }
    fprintf(stderr, "test_kann: error rate %.2f%% (%d/200)\n", 100.0*n_err/200, n_err);

    kann_delete(ann);
    if (n_err * 100 / 200 < 10) { printf("test kann 0: OK\n"); return 0; }
    fprintf(stderr, "test_kann: not converged\n");
    return 1;
}
