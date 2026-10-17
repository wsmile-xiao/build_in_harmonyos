/*
 * test_package.c — cranium-ml 消费者测试
 *
 * 仅通过库公开头文件 <cranium.h> 使用公开 API：
 *   createMatrixZeroes / setMatrix / getMatrix / multiply / equals / destroyMatrix
 * 断言矩阵运算真实结果，可观察输出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <cranium.h>

static int check_matrix_ops(void) {
    /* 2x2 矩阵 A = [[1,2],[3,4]]；createMatrix 只持有 data 指针，
     * destroyMatrix 会 free(matrix->data)，故 data 必须是堆内存 */
    float *a_data = (float *)malloc(4 * sizeof(float));
    a_data[0] = 1.0f; a_data[1] = 2.0f; a_data[2] = 3.0f; a_data[3] = 4.0f;
    Matrix *A = createMatrix(2, 2, a_data);
    if (!A) { printf("FAIL: createMatrix returned NULL\n"); return 1; }

    /* B = A * A = [[7,10],[15,22]] */
    Matrix *B = multiply(A, A);
    if (!B) { printf("FAIL: multiply returned NULL\n"); destroyMatrix(A); return 1; }

    int ok = 1;
    if (getMatrix(B, 0, 0) != 7.0f) { printf("FAIL: B[0][0]=%f != 7\n", getMatrix(B, 0, 0)); ok = 0; }
    if (getMatrix(B, 1, 1) != 22.0f) { printf("FAIL: B[1][1]=%f != 22\n", getMatrix(B, 1, 1)); ok = 0; }

    /* C = 零矩阵，验证 setMatrix 写入 */
    Matrix *C = createMatrixZeroes(2, 2);
    setMatrix(C, 0, 1, 5.0f);
    if (getMatrix(C, 0, 1) != 5.0f) { printf("FAIL: C[0][1]=%f != 5\n", getMatrix(C, 0, 1)); ok = 0; }

    if (ok) printf("OK: matrix add/multiply/set/get semantics verified (B[0][0]=%f B[1][1]=%f C[0][1]=%f)\n",
                   getMatrix(B, 0, 0), getMatrix(B, 1, 1), getMatrix(C, 0, 1));

    destroyMatrix(A);
    destroyMatrix(B);
    destroyMatrix(C);
    return ok ? 0 : 1;
}

static int check_network_api(void) {
    /* 3 -> 4 -> 2 小型网络：仅验证公开网络 API 可正常构造/前向/销毁 */
    size_t hidden[1] = {4};
    Activation acts[2];
    acts[0] = sigmoid;
    acts[1] = softmax;
    Network *net = createNetwork(3, 1, hidden, acts, 2, softmax);
    if (!net) { printf("FAIL: createNetwork returned NULL\n"); return 1; }

    /* 用 DataSet 前向（上游网络测试的公开用法：forwardPassDataSet） */
    float **rows = (float **)malloc(sizeof(float *) * 2);
    int i;
    for (i = 0; i < 2; i++) {
        rows[i] = (float *)malloc(sizeof(float) * 3);
        rows[i][0] = 0.5f; rows[i][1] = -0.2f; rows[i][2] = 0.9f;
    }
    DataSet *example = createDataSet(2, 3, rows);
    forwardPassDataSet(net, example);
    Matrix *out = getOuput(net);
    if (!out) { printf("FAIL: getOuput returned NULL\n"); destroyDataSet(example); destroyNetwork(net); return 1; }

    printf("OK: network forward pass produced %zu outputs (first=%f)\n",
           out->cols, getMatrix(out, 0, 0));

    destroyDataSet(example);
    /* destroyDataSet 已释放 rows 各元素及 rows 数组本身，不得再次 free */
    destroyNetwork(net);
    return 0;
}

int main(void) {
    int rc = 0;
    rc |= check_matrix_ops();
    rc |= check_network_api();
    if (rc == 0) printf("ALL CONSUMER TESTS PASSED\n");
    return rc;
}
