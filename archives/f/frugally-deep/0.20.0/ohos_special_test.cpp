// frugally-deep 0.20.0 HarmonyOS 专项测试（真实消费入口验证）
//
// 上游单元测试的模型数据由 keras_export/*.py 依赖 TensorFlow/Keras 生成，
// OHOS aarch64 环境无 TF 轮子（见测试台账），故本用例改为内联构造一个
// 最小合法 fdeep 模型 JSON（单 Dense 层，y = 2x + 1），经 fdeep 公开 API
// read_model_from_string() 解析、predict() 推理，并对输出做数值断言。
// 覆盖库的核心公开 API 调用与可观察结果，在 OHOS 工具链下实际编译运行。
#include <cmath>
#include <cstdio>
#include <string>

#include <fdeep/fdeep.hpp>

static const char* kModelJson = R"json(
{
  "image_data_format": "channels_last",
  "architecture": {
    "class_name": "Sequential",
    "config": {
      "name": "sequential_1",
      "layers": [
        {"class_name": "InputLayer", "name": "input_1", "config": {"batch_shape": [1, 1]}, "inbound_nodes": []},
        {"class_name": "Dense", "name": "dense_1", "config": {"name": "dense_1", "units": 1, "use_bias": true},
         "inbound_nodes": [{"args": [{"config": {"keras_history": ["input_1", 0, 0]}}]}]}
      ],
      "input_layers": [["input_1", 0, 0]],
      "output_layers": [["dense_1", 0, 0]]
    }
  },
  "input_shapes": [[1]],
  "output_shapes": [[1]],
  "trainable_params": {
    "dense_1": {"weights": [2.0], "bias": [1.0]}
  }
}
)json";

int main()
{
    int failures = 0;

    // 1) 公开 API：read_model_from_string 解析内联模型
    const auto model = fdeep::read_model_from_string(kModelJson, false, fdeep::cout_logger);
    std::printf("model name: %s\n", model.name().c_str());

    // 2) 公开 API：predict 单次前向，输入 x=3.0
    const auto result = model.predict(
        {fdeep::tensor(fdeep::tensor_shape(static_cast<std::size_t>(1)),
            fdeep::float_vec{3.0f})});

    // 3) 可观察断言：期望输出 y = 2*3 + 1 = 7.0
    const auto out = fdeep::show_tensors(result);
    std::printf("predict output: %s\n", out.c_str());

    const float got = result[0].get(fdeep::tensor_pos(static_cast<std::size_t>(0)));
    const float expected = 7.0f;
    if (std::fabs(got - expected) > 1e-4f) {
        std::printf("FAIL: expected %.4f, got %.4f\n", expected, got);
        failures++;
    } else {
        std::printf("PASS: dense output %.4f == expected %.4f\n", got, expected);
    }

    // 4) predict_single_output 便捷公开 API 一致性
    const float single = model.predict_single_output(
        {fdeep::tensor(fdeep::tensor_shape(static_cast<std::size_t>(1)),
            fdeep::float_vec{3.0f})});
    std::printf("predict_single_output: %.4f\n", single);
    if (std::fabs(single - expected) > 1e-4f) {
        std::printf("FAIL: predict_single_output mismatch\n");
        failures++;
    }

    if (failures == 0) {
        std::printf("OHOS_SPECIAL_TEST_RESULT: PASS (0 failures)\n");
        return 0;
    }
    std::printf("OHOS_SPECIAL_TEST_RESULT: FAIL (%d failures)\n", failures);
    return 1;
}