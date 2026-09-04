// test_libsvm_ohos.cpp — libsvm HarmonyOS 特有测试（4 用例）
//
// 针对鸿蒙平台特性：
//   1. LIBSVM_VERSION=337 断言（HarmonyOS 工具链下头文件版本身份）
//   2. 线性核训练 + 预测——2D 线性可分合成数据集 40 样本 100% 正确
//   3. svm_save_model/svm_load_model 模型往返——真文件保存/加载，
//      预测一致性（覆盖共享库文件 IO 路径）
//   4. RBF 核 + svm_predict_values——决策函数值有限且预测标签正确
//
// Usage: test_libsvm_ohos
#include <svm.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <unistd.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                                  \
    do {                                                                  \
        if (cond) {                                                       \
            std::printf("[PASS] %s\n", (msg));                            \
        } else {                                                          \
            std::fprintf(stderr, "[FAIL] %s (line %d)\n", (msg), __LINE__); \
            g_failures++;                                                 \
        }                                                                 \
    } while (0)

// 2D 合成数据集：40 样本，两个线性可分簇
static const int N = 40;
static double g_y[N];
static struct svm_node g_x[N][3]; // [i] = {f1, f2, {-1,0} 终止符（libsvm 约定）}

static void fill_nodes(struct svm_node *x, double v1, double v2)
{
    x[0].index = 1;
    x[0].value = v1;
    x[1].index = 2;
    x[1].value = v2;
    x[2].index = -1; // libsvm 约定：index == -1 作为样本终止标记
    x[2].value = 0.0;
}

static struct svm_node *g_xp[N]; // 每样本节点指针（svm_problem.x 元素）

static void make_dataset(void)
{
    for (int i = 0; i < N / 2; i++) {
        // 类 +1: (1..3, 1..3)
        g_y[i] = 1.0;
        fill_nodes(g_x[i], 1.0 + (i % 4) * 0.6, 1.0 + (i / 4 % 4) * 0.6);
        g_xp[i] = g_x[i];
    }
    for (int i = N / 2; i < N; i++) {
        // 类 -1: (-3..-1, -3..-1)
        int j = i - N / 2;
        g_y[i] = -1.0;
        fill_nodes(g_x[i], -(1.0 + (j % 4) * 0.6), -(1.0 + (j / 4 % 4) * 0.6));
        g_xp[i] = g_x[i];
    }
}

static struct svm_parameter make_param(int svm_type, int kernel_type)
{
    struct svm_parameter p;
    p.svm_type = svm_type;
    p.kernel_type = kernel_type;
    p.degree = 3;
    p.gamma = (kernel_type == RBF) ? 1.0 : 0.0;
    p.coef0 = 0.0;
    p.cache_size = 64;
    p.eps = 1e-3;
    p.C = 10.0;
    p.nr_weight = 0;
    p.weight_label = nullptr;
    p.weight = nullptr;
    p.nu = 0.5;
    p.p = 0.1;
    p.shrinking = 1;
    p.probability = 0;
    return p;
}

int main(void)
{
    make_dataset();
    struct svm_problem prob;
    prob.l = N;
    prob.x = g_xp;
    prob.y = g_y;

    // ── 用例 1: 版本断言 ──
    CHECK(LIBSVM_VERSION == 337, "case1: LIBSVM_VERSION == 337");

    // ── 用例 2: 线性核训练 + 预测（100% 正确）──
    struct svm_parameter param_lin = make_param(C_SVC, LINEAR);
    struct svm_model *m_lin = svm_train(&prob, &param_lin);
    CHECK(m_lin != nullptr, "case2: svm_train(C_SVC, LINEAR) 成功");
    int correct = 0;
    if (m_lin) {
        for (int i = 0; i < N; i++) {
            if (svm_predict(m_lin, g_x[i]) == g_y[i])
                correct++;
        }
    }
    CHECK(correct == N, "case2: 线性核预测 40/40 全对");

    // ── 用例 3: 模型保存/加载往返（真文件 IO）──
    const char *td = std::getenv("TMPDIR");
    std::string mpath = std::string(td && *td ? td : "/tmp") +
                        "/libsvm_ohos_test_" + std::to_string(::getpid()) + ".model";
    int saved = (m_lin != nullptr) ? svm_save_model(mpath.c_str(), m_lin) : 1;
    struct svm_model *m_loaded =
        (saved == 0) ? svm_load_model(mpath.c_str()) : nullptr;
    CHECK(m_loaded != nullptr && m_lin != nullptr,
          "case3: svm_save_model + svm_load_model 往返成功");
    int match = 0;
    if (m_loaded && m_lin) {
        for (int i = 0; i < N; i++) {
            if (svm_predict(m_loaded, g_x[i]) == svm_predict(m_lin, g_x[i]))
                match++;
        }
    }
    CHECK(match == N, "case3: 加载模型预测与原模型一致 40/40");
    std::remove(mpath.c_str());
    if (m_loaded)
        svm_free_and_destroy_model(&m_loaded);
    if (m_lin)
        svm_free_and_destroy_model(&m_lin);

    // ── 用例 4: RBF 核 + 决策函数 ──
    struct svm_parameter param_rbf = make_param(C_SVC, RBF);
    struct svm_model *m_rbf = svm_train(&prob, &param_rbf);
    CHECK(m_rbf != nullptr, "case4: svm_train(C_SVC, RBF) 成功");
    double dec_pos = 0.0, dec_neg = 0.0;
    double p_pos = 0.0, p_neg = 0.0;
    if (m_rbf) {
        p_pos = svm_predict_values(m_rbf, g_x[0], &dec_pos);       // 类 +1 样本
        p_neg = svm_predict_values(m_rbf, g_x[N / 2], &dec_neg);   // 类 -1 样本
    }
    CHECK(std::isfinite(dec_pos) && std::isfinite(dec_neg) &&
              p_pos == 1.0 && p_neg == -1.0,
          "case4: RBF svm_predict_values 决策函数有限且标签正确");
    if (m_rbf)
        svm_free_and_destroy_model(&m_rbf);

    if (g_failures == 0) {
        std::printf("OK: libsvm 3.37 HarmonyOS 特有测试 4/4 全过\n");
        return 0;
    }
    std::fprintf(stderr, "FAILED: %d 个鸿蒙特有测试用例失败\n", g_failures);
    return 1;
}
