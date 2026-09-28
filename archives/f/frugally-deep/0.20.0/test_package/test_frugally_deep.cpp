// test_package 消费者验证：通过包导出的公开头文件与公开 API，
// 解析一个最小 Dense 模型（y = 2x + 1）并验证 predict 输出，属真实消费者用例。
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
    const auto model = fdeep::read_model_from_string(kModelJson, false, nullptr);
    const auto result = model.predict(
        {fdeep::tensor(fdeep::tensor_shape(static_cast<std::size_t>(1)),
            fdeep::float_vec{3.0f})});
    const float got = result[0].get(fdeep::tensor_pos(static_cast<std::size_t>(0)));
    if (std::fabs(got - 7.0f) > 1e-4f) {
        std::printf("CONSUMER_TEST FAIL: expected 7.0, got %.4f\n", got);
        return 1;
    }
    std::printf("CONSUMER_TEST PASS: fdeep::read_model_from_string + predict -> %.4f\n", got);
    return 0;
}