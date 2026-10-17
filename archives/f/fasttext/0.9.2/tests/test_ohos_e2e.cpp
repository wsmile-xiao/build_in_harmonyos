// test_ohos_e2e.cpp — HarmonyOS 专项测试（fasttext 0.9.2）
//
// 目的：在 OHOS aarch64 工具链产物（conan 包 libfasttext.a + include/fasttext/*.h）
// 上真实走通 fasttext::FastText::train → saveModel → loadModel → predictLine
// 完整公开 API 管线，验证库在 HarmonyOS 平台可编译、可链接、可调用并产出
// 真实可观测的分类结果（训练集内一致性 + 训练集外预测非空且标签正确率 ≥ 0.6）。
//
// 该测试为鸿蒙专项测试，独立于上游 Python unittest（83 单元 + 13 集成）
// 与 test_package 消费者用例（同类 API 冒烟），单独计数（见 notes.md 台账）。
//
// 编译（OHOS 工具链，与 conan 包一致）：
//   /data/service/hnp/bin/clang++ -O2 -std=c++11 -pthread \
//     -I$PACKAGE/include test_ohos_e2e.cpp $PACKAGE/lib/libfasttext.a \
//     -lm -lpthread -o test_ohos_e2e
// 运行：./test_ohos_e2e
#include <fasttext/args.h>
#include <fasttext/fasttext.h>

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

// 训练集：cooking 风格短文本二分类（10 正 10 负，含训练集外句子）
static const char* TRAIN_SAMPLES[] = {
    "__label__positive this dish is delicious and tasty",
    "__label__positive i love the flavor of this soup",
    "__label__positive the cake is sweet and soft",
    "__label__positive grilled chicken with herbs tastes great",
    "__label__positive fresh vegetables make a wonderful salad",
    "__label__positive the pasta is creamy and full of cheese",
    "__label__positive this coffee is aromatic and rich",
    "__label__positive the bread is warm and freshly baked",
    "__label__positive the sauce has a perfect balance of spices",
    "__label__positive i enjoy the crunchy texture of the nuts",
    "__label__negative this dish is bland and tasteless",
    "__label__negative the soup is too salty and watery",
    "__label__negative the cake is dry and burnt",
    "__label__negative the chicken is tough and overcooked",
    "__label__negative the salad is wilted and stale",
    "__label__negative the pasta is mushy and flavorless",
    "__label__negative this coffee is bitter and cold",
    "__label__negative the bread is stale and hard",
    "__label__negative the sauce is greasy and heavy",
    "__label__negative i dislike the slimy texture of the pudding",
};
static const size_t N_TRAIN = sizeof(TRAIN_SAMPLES) / sizeof(TRAIN_SAMPLES[0]);

// 训练集外验证句（4 正 4 负）
static const char* VALID_SAMPLES[] = {
    "this stew is hearty and comforting",      // positive
    "the ice cream is creamy and sweet",       // positive
    "the salad tastes fresh and crisp",        // positive
    "the pie is flaky and delightful",         // positive
    "the stew is lumpy and watery",            // negative
    "the ice cream is icy and tasteless",      // negative
    "the pie is soggy and burned",             // negative
    "the salad is wilted and sour",            // negative
};
static const char* VALID_EXPECTED[] = {
    "positive", "positive", "positive", "positive",
    "negative", "negative", "negative", "negative",
};
static const size_t N_VALID = sizeof(VALID_SAMPLES) / sizeof(VALID_SAMPLES[0]);

int main() {
  const char* kTrain = "ft_ohos_train.txt";
  {
    std::ofstream out(kTrain);
    for (size_t i = 0; i < N_TRAIN; ++i) {
      out << TRAIN_SAMPLES[i] << "\n";
    }
  }

  fasttext::Args args;
  args.input = kTrain;
  args.output = "ft_ohos_model";
  args.epoch = 100;
  args.lr = 0.5;
  args.dim = 20;
  args.wordNgrams = 2;
  args.minCount = 1;
  args.thread = 1;
  args.verbose = 0;
  args.model = fasttext::model_name::sup;  // 监督模型，否则 predictLine 拒绝预测

  fasttext::FastText ft;
  ft.train(args);                 // 公开 API: 训练
  ft.saveModel("ft_ohos_model.bin");  // 公开 API: 保存

  fasttext::FastText loaded;
  loaded.loadModel("ft_ohos_model.bin");  // 公开 API: 加载

  // 训练集内一致性检查
  int train_hits = 0;
  for (size_t i = 0; i < N_TRAIN; ++i) {
    std::string line(TRAIN_SAMPLES[i]);
    std::string expected = line.substr(0, line.find(' '));
    expected = expected.substr(strlen("__label__"));
    std::istringstream in(TRAIN_SAMPLES[i]);
    std::vector<std::pair<fasttext::real, std::string>> preds;
    bool ok = loaded.predictLine(in, preds, 1, 0.0);
    if (ok && !preds.empty() && preds[0].second.find(expected) != std::string::npos)
      ++train_hits;
  }
  double train_acc = double(train_hits) / double(N_TRAIN);

  // 训练集外预测检查
  int valid_hits = 0;
  for (size_t i = 0; i < N_VALID; ++i) {
    std::istringstream in(VALID_SAMPLES[i]);
    std::vector<std::pair<fasttext::real, std::string>> preds;
    bool ok = loaded.predictLine(in, preds, 1, 0.0);
    if (ok && !preds.empty() &&
        preds[0].second.find(VALID_EXPECTED[i]) != std::string::npos)
      ++valid_hits;
  }
  double valid_acc = double(valid_hits) / double(N_VALID);

  std::printf("train_acc=%.3f (%d/%zu)\n", train_acc, train_hits, N_TRAIN);
  std::printf("valid_acc=%.3f (%d/%zu)\n", valid_acc, valid_hits, N_VALID);

  std::remove(kTrain);
  std::remove("ft_ohos_model.bin");

  // 门禁：训练集内一致性 ≥ 0.9 且训练集外正确率 ≥ 0.6（真实可观测结果，非空壳）
  if (train_acc < 0.9 || valid_acc < 0.6) {
    std::fprintf(stderr, "FAIL: accuracy below gate (train>=0.9, valid>=0.6)\n");
    return 1;
  }
  std::printf("OHOS e2e test: OK\n");
  return 0;
}