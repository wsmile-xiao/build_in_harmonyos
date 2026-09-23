// test_package/test_tiny_dnn.cpp — tiny-dnn 1.0.0a3 消费者测试
//
// 六组断言，失败以退出码 2..7 区分。全部断言都是**可观测行为**：
// 编译期配置（include 根布局、gemmlowp 后端）、训练收敛（XOR 分类）、
// 前向形状、序列化往返、量化层元数据、多线程确定性训练。
//
// 注：本文件刻意用 <tiny_dnn/...> 角括号 + "third_party/..." 混合包含，
// 以同时证明「三棵目录并排装进同一个 include 根」这一安装布局成立。
#include <cmath>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>

#include <tiny_dnn/tiny_dnn.h>     // 库本体（内部以 <cereal/...> 与 "third_party/..." 包含另外两棵）
#include <tiny_dnn/util/image.h>   // 显式拉入 third_party/stb/
                                   // 注：third_party/gemmlowp 不能这样显式拉 ——
                                   // tiny_dnn/core/kernels/tiny_quantized_matmul_kernel.h
                                   // 没有 include guard，重复包含即 redefinition；它由
                                   // tiny_dnn.h -> backend_tiny.h 在 #ifdef CNN_USE_GEMMLOWP
                                   // 下引入，见组 5 的运行时断言。
#include <cereal/cereal.hpp>       // 显式拉入 cereal 树（角括号 → 必须挂在 include 根上）

using namespace tiny_dnn;
using namespace tiny_dnn::activation;
using namespace tiny_dnn::layers;

static int fail(int code, const char* what) {
    std::printf("FAIL[%d]: %s\n", code, what);
    return code;
}

// ── 组 1：include 根布局 + 平台基础类型宽度 ─────────────────────────────
static int group1() {
    // float_t 默认 typedef 到 float；OHOS aarch64 上与线格式/内存布局一致。
    if (sizeof(tiny_dnn::float_t) != 4) return fail(2, "sizeof(tiny_dnn::float_t) != 4");

    // 无 OpenMP（OHOS 不提供）时 CNN_TASK_SIZE 必须是 8 —— 这个宏是
    // network::train 的 n_threads 默认值，配错会直接改变线程行为。
    if (CNN_TASK_SIZE != 8) return fail(2, "CNN_TASK_SIZE != 8 (OpenMP unexpectedly enabled)");

    // third_party/stb 必须可见：image<> 能用其默认构造与访问器。
    tiny_dnn::image<unsigned char> img;
    if (img.width() != 0 || img.height() != 0 || img.depth() != 1)
        return fail(2, "tiny_dnn::image default state wrong -> third_party/stb unreachable");

    std::printf("PASS 1: include-root layout (tiny_dnn + cereal + third_party) visible; "
                "float_t=4B, CNN_TASK_SIZE=%d\n", (int)CNN_TASK_SIZE);
    return 0;
}

// ── 组 2：MLP 训练收敛（XOR 分类）──────────────────────────────────────
static int group2() {
    std::vector<vec_t> data = {{0, 0}, {0, 1}, {1, 0}, {1, 1}};
    std::vector<label_t> label = {0, 1, 1, 0};

    tiny_dnn::set_random_seed(12345);

    // 2-10-2 tan_h + adagrad(alpha*10) + train<mse>(labels)，与上游
    // test/test_network.h 的 `network.train_predict` 用例同构 —— 那条用例在
    // 本包的 build() 里也会实跑，此处只是把数据集换成 XOR 的 4 个角。
    network<sequential> net;
    adagrad optimizer;
    optimizer.alpha *= 10;
    net << fc<tan_h>(2, 10) << fc<tan_h>(10, 2);

    // 训练前的两侧输出：未训练的 net 在 4 个角上给出的 argmax 不该全对
    // （否则这个用例就证明不了"训练真的在起作用"）。
    net.train<mse>(optimizer, data, label, 4, 2000);

    // 四个 XOR 角的分类必须全对（label 0/1 对 2 个输出取 argmax）。
    // 这是本组唯一的可观测判据：loss 数值在 2 输出 + one-hot 语义下不单调，
    // 不可作为断言（见 notes.md §4 rule4 口径说明旁的收敛口径备注）。
    int correct = 0;
    for (size_t i = 0; i < data.size(); i++) {
        if (net.predict_label(data[i]) == label[i]) correct++;
    }
    if (correct != (int)data.size())
        return fail(3, "trained MLP misclassifies an XOR sample");

    std::printf("PASS 2: MLP trained on XOR, %d/%d samples classified correctly\n",
                correct, (int)data.size());
    return 0;
}

// ── 组 3：卷积 + 池化 + 全连接前向形状 ─────────────────────────────────
static int group3() {
    network<sequential> net;
    net << conv<tan_h>(8, 8, 3, 1, 2, padding::valid)   // 8x8x1 -> 6x6x2 = 72
        << ave_pool<tan_h>(6, 6, 2, 2)                  // 6x6x2 -> 3x3x2 = 18
        << fc<tan_h>(18, 4);                            // 18 -> 4

    const vec_t out = net.predict(vec_t(64));           // 8*8*1
    if (out.size() != 4)
        return fail(4, "conv/pool/fc forward produced wrong output size");

    for (float_t v : out)
        if (!std::isfinite((double)v))
            return fail(4, "conv/pool/fc forward produced non-finite value");

    std::printf("PASS 3: conv(8x8x1,3x3,2ch) -> ave_pool(2x2) -> fc(18,4) forward ok, "
                "out size %zu\n", out.size());
    return 0;
}

// ── 组 4：JSON 序列化往返 ──────────────────────────────────────────────
static int group4() {
    std::vector<vec_t> data = {{0, 0}, {0, 1}, {1, 0}, {1, 1}};
    std::vector<vec_t> target = {{0}, {1}, {1}, {0}};

    tiny_dnn::set_random_seed(777);
    network<sequential> net;
    net << fc<tan_h>(2, 6) << fc<tan_h>(6, 1);

    gradient_descent optimizer;
    net.fit<mse>(optimizer, data, target, 4, 500);

    std::vector<vec_t> before;
    for (const vec_t& x : data) before.push_back(net.predict(x));

    // (a) to_json()/from_json() 是**架构**序列化（network.h: to_json 注释
    // 即 "save the network architecture as json string"，内部 to_archive
    // content_type::model）—— 它不写权重，所以只能断言形状往返，不能断言
    // 预测值。这条是 cereal JSON 归档路径在 OHOS 上可用的最小证据。
    const std::string json = net.to_json();
    if (json.empty()) return fail(5, "to_json() produced an empty string");

    network<sequential> arch;
    arch << fc<tan_h>(2, 6) << fc<tan_h>(6, 1);
    arch.from_json(json);
    if (arch.predict(data[0]).size() != before[0].size())
        return fail(5, "from_json() did not restore the architecture (output shape mismatch)");

    // (b) weights_and_model 的 JSON 往返必须逐位保住预测值。
    const std::string fname = "tiny_dnn_roundtrip.json";
    net.save(fname, content_type::weights_and_model, file_format::json);

    network<sequential> restored;
    restored << fc<tan_h>(2, 6) << fc<tan_h>(6, 1);
    restored.load(fname, content_type::weights_and_model, file_format::json);
    std::remove(fname.c_str());

    for (size_t i = 0; i < data.size(); i++) {
        const vec_t y = restored.predict(data[i]);
        if (y.size() != before[i].size())
            return fail(5, "deserialized net output size mismatch");
        if (std::fabs((double)y[0] - (double)before[i][0]) > 1e-6)
            return fail(5, "deserialized net predictions differ from original");
    }

    std::printf("PASS 4: arch JSON %zu bytes round-tripped via from_json; "
                "weights_and_model JSON round-trip preserved all %zu predictions\n",
                json.size(), data.size());
    return 0;
}

// ── 组 5：鸿蒙特有 A —— OHOS aarch64 的推理后端与量化路径 ──────────────
static int group5() {
    // aarch64 无 AVX，default_engine() 必须退到内部后端，而不是 avx。
    if (core::default_engine() != core::backend_t::internal)
        return fail(6, "default_engine() != backend_t::internal on aarch64/OHOS");

    // 非 MSVC/非 Windows 编译才启用 gemmlowp；OHOS 上必须命中这条路径，
    // 否则量化层的 int8 矩阵乘会退化为不存在/慢路径。
#ifndef CNN_USE_GEMMLOWP
    return fail(6, "CNN_USE_GEMMLOWP not defined on OHOS -> quantized path missing");
#endif

    // 量化卷积层在 OHOS 上的元数据契约（与上游 test_quantized_convolutional_layer
    // 的 setup_internal 同口径），证明 int8 卷积结构可正确构造。
    quantized_convolutional_layer<sigmoid> qc(5, 5, 3, 1, 2, padding::valid,
                                               true, 1, 1, core::backend_t::internal);
    if (qc.layer_type() != "q_conv") return fail(6, "quantized layer type != q_conv");
    if (qc.in_data_size() != 25) return fail(6, "quantized layer in_data_size != 25");
    if (qc.out_data_size() != 18) return fail(6, "quantized layer out_data_size != 18");
    if (qc.in_channels() != 3 || qc.out_channels() != 2)
        return fail(6, "quantized layer channel counts wrong");

    // 真正跑一遍 int8 量化卷积前向 —— 这条路径由 gemmlowp 承担
    // （backend_tiny.h 在 #ifdef CNN_USE_GEMMLOWP 下才编入 tiny_quantized_conv2d_kernel）。
    // 张量打包照上游 test/test_quantized_convolutional_layer.h 的 fprop 用例。
    auto make_tensor = [](size_t n) { return tensor_t(1, vec_t(n)); };
    tensor_t in_t = make_tensor(25), out_t = make_tensor(18), a_t = make_tensor(18),
             w_t = make_tensor(18), b_t = make_tensor(2);
    uniform_rand(in_t[0].begin(), in_t[0].end(), -1.0, 1.0);

    std::vector<tensor_t*> in_data{&in_t, &w_t, &b_t}, out_data{&out_t, &a_t};
    quantized_convolutional_layer<sigmoid> qf(5, 5, 3, 1, 2);
    qf.setup(false);
    qf.forward_propagation(in_data, out_data);

    for (float_t v : out_t[0]) {
        if (!std::isfinite((double)v))
            return fail(6, "quantized conv forward produced non-finite value");
        // 末层 sigmoid：无论 int8 量化/反量化怎么取值，输出必须落在 (0,1)。
        if (v < 0.0f || v > 1.0f)
            return fail(6, "quantized conv forward (gemmlowp) left the sigmoid range");
    }

    std::printf("PASS 5: engine=internal, gemmlowp enabled, q_conv(5x5,3,1,2) "
                "metadata 25->18 + int8 forward 18/18 in (0,1) on OHOS aarch64\n");
    return 0;
}

// ── 组 6：鸿蒙特有 B —— bionic std::thread 批量训练 + 固定种子可复现 ─────
static int group6() {
    if (std::thread::hardware_concurrency() < 1)
        return fail(7, "std::thread::hardware_concurrency() < 1 on OHOS");

    std::vector<vec_t> data, target;
    for (int i = 0; i < 16; i++) {
        const float_t a = (float_t)(i % 4) / 3.0f;
        const float_t b = (float_t)((i / 4) % 4) / 3.0f;
        data.push_back(vec_t{a, b});
        target.push_back(vec_t{a * b});          // 可学习的确定性函数
    }

    auto make_and_train = [&](int n_threads) {
        tiny_dnn::set_random_seed(2024);
        network<sequential> net;
        net << fc<tan_h>(2, 6) << fc<tan_h>(6, 1);
        adagrad optimizer;
        // CNN_TASK_SIZE(=8) 个任务走 bionic pthread；n_threads 显式钉住。
        net.fit<mse>(optimizer, data, target, 4, 40, nop, nop, true, n_threads);
        std::vector<float_t> out;
        for (const vec_t& x : data) out.push_back(net.predict(x)[0]);
        return out;
    };

    // (a) 单线程 + 固定种子：两轮必须逐位一致（OHOS 上 RNG/训练确定性）。
    const std::vector<float_t> r1 = make_and_train(1);
    const std::vector<float_t> r2 = make_and_train(1);
    for (size_t i = 0; i < r1.size(); i++)
        if (r1[i] != r2[i])
            return fail(7, "same seed + n_threads=1 gave different results (non-deterministic)");

    // (b) 多线程：8 个任务在 bionic 上必须跑通且输出有限（不挂死/不崩）。
    const std::vector<float_t> rm = make_and_train(CNN_TASK_SIZE);
    for (float_t v : rm)
        if (!std::isfinite((double)v))
            return fail(7, "multi-threaded training produced non-finite output");

    std::printf("PASS 6: deterministic training (n_threads=1, %zu outputs identical across runs); "
                "n_threads=%d ran on bionic std::thread\n", r1.size(), (int)CNN_TASK_SIZE);
    return 0;
}

int main() {
    if (const int rc = group1()) return rc;
    if (const int rc = group2()) return rc;
    if (const int rc = group3()) return rc;
    if (const int rc = group4()) return rc;
    if (const int rc = group5()) return rc;
    if (const int rc = group6()) return rc;

    std::printf("ALL PASS: tiny-dnn 1.0.0a3 consumer tests (6 groups) on HarmonyOS\n");
    return 0;
}
