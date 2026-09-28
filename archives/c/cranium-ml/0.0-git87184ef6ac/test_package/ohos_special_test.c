/*
 * ohos_special_test.c — cranium-ml HarmonyOS 专项测试
 *
 * 通过公开头文件 <cranium.h> 与公开训练 API（createNetwork / createDataSet /
 * batchGradientDescent / forwardPassDataSet / meanSquaredError）在 OHOS PC
 * (aarch64) 上训练一个 XOR 网络，断言训练前后均方误差真实下降（收敛行为可观察），
 * 并验证输出层规模与数值有限性。与上游 matrix/function/layer/network/optimizer
 * 五个测试程序相互独立（上游不做收敛断言，仅打印过程）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <cranium.h>

static float loss_of(Network *net, DataSet *actual) {
    Matrix *pred = getOuput(net);
    return meanSquaredError(net, pred, actual, 0.0f);
}

int main(void) {
    /* XOR 数据集：4 行 2 列，标签 4 行 1 列（全部显式初始化，避免未初始化内存） */
    float **inputs = (float **)malloc(4 * sizeof(float *));
    float **labels = (float **)malloc(4 * sizeof(float *));
    int i;
    for (i = 0; i < 4; i++) {
        inputs[i] = (float *)malloc(2 * sizeof(float));
        labels[i] = (float *)malloc(1 * sizeof(float));
    }
    inputs[0][0] = 0.0f; inputs[0][1] = 0.0f; labels[0][0] = 0.0f;
    inputs[1][0] = 0.0f; inputs[1][1] = 1.0f; labels[1][0] = 1.0f;
    inputs[2][0] = 1.0f; inputs[2][1] = 0.0f; labels[2][0] = 1.0f;
    inputs[3][0] = 1.0f; inputs[3][1] = 1.0f; labels[3][0] = 0.0f;

    DataSet *data = createDataSet(4, 2, inputs);
    DataSet *classes = createDataSet(4, 1, labels);

    /* 2 -> 3 -> 1 网络，隐藏层 sigmoid，输出 sigmoid（回归 XOR） */
    size_t hidden[1] = {3};
    Activation acts[1];
    acts[0] = sigmoid;
    Network *net = createNetwork(2, 1, hidden, acts, 1, sigmoid);
    if (!net) { printf("FAIL: createNetwork returned NULL\n"); return 1; }

    /* 训练前损失（公开 API meanSquaredError，需真实标签） */
    forwardPassDataSet(net, data);
    float loss_before = loss_of(net, classes);
    if (!isfinite(loss_before)) { printf("FAIL: loss_before not finite: %f\n", loss_before); return 1; }

    /* 批量梯度下降：MEAN_SQUARED_ERROR，batch=4，lr=1.0，search=0，reg=0，
     * momentum=0，500 轮，不 shuffle，静默 */
    batchGradientDescent(net, data, classes, MEAN_SQUARED_ERROR, 4,
                         1.0f, 0.0f, 0.0f, 0.0f, 500, 0, 0);

    /* 训练后损失：batchGradientDescent 后输出层残留最后一批行数，
     * 先重放全量数据集前向，再取损失（与上游 verbose 分支同法） */
    forwardPassDataSet(net, data);
    Matrix *pred = getOuput(net);
    if (!pred) { printf("FAIL: getOuput returned NULL\n"); return 1; }
    if (pred->cols != 1) { printf("FAIL: output cols=%zu != 1\n", pred->cols); return 1; }
    float loss_after = loss_of(net, classes);
    if (!isfinite(loss_after)) { printf("FAIL: loss_after not finite: %f\n", loss_after); return 1; }

    printf("OHOS-SPECIAL: loss_before=%f loss_after=%f reduction=%f%%\n",
           loss_before, loss_after, (1.0f - loss_after / loss_before) * 100.0f);

    /* 收敛断言：损失必须真实下降（至少 10%），证明 OHOS 上训练流程可运行且有效 */
    if (loss_after >= loss_before * 0.9f) {
        printf("FAIL: loss did not converge (before=%f after=%f)\n", loss_before, loss_after);
        destroyNetwork(net);
        destroyDataSet(data);
        destroyDataSet(classes);
        return 1;
    }

    printf("OK: OHOS XOR training converged (MSE %f -> %f)\n", loss_before, loss_after);

    destroyNetwork(net);
    destroyDataSet(data);
    destroyDataSet(classes);
    return 0;
}
