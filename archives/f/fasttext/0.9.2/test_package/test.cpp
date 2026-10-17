// test_package consumer test — fasttext 0.9.2
//
// R34: 必须真实调用被测库的公开 API 并验证可观察结果，禁止空壳 print。
// 本用例：通过公开头文件（fasttext/fasttext.h, fasttext/args.h）与
// 公开 API（FastText::train / predictLine）训练一个微型监督模型并预测，
// 验证第三方消费者可以编译、链接、调用并得到真实结果。
#include <fasttext/args.h>
#include <fasttext/fasttext.h>

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

int main() {
  // 1. 构造一块微型训练数据（带 __label__ 前缀的真实分类样本）
  const char* kTrain = "ft_test_train.txt";
  {
    std::ofstream out(kTrain);
    out << "__label__pos this film is great and beautiful\n"
        << "__label__neg this movie is boring and terrible\n"
        << "__label__pos what a wonderful story\n"
        << "__label__neg i dislike this plot\n";
  }

  // 2. 使用公开 API 训练监督模型
  fasttext::Args args;
  args.input = kTrain;
  args.output = "ft_test_model";
  args.epoch = 10;
  args.lr = 0.2;
  args.dim = 5;
  args.minCount = 1;
  args.thread = 1;
  args.verbose = 0;
  args.model = fasttext::model_name::sup;  // 监督模型，否则 predictLine 拒绝预测

  fasttext::FastText ft;
  ft.train(args);

  // 3. 使用公开 API predictLine 预测，验证非空标签输出
  std::istringstream line("this story is great");
  std::vector<std::pair<fasttext::real, std::string>> predictions;
  bool ok = ft.predictLine(line, predictions, 1, 0.0);
  if (!ok || predictions.empty()) {
    std::fprintf(stderr, "FAIL: predictLine returned no prediction\n");
    return 1;
  }
  std::printf("prediction: %s (%.6f)\n",
              predictions[0].second.c_str(), predictions[0].first);
  std::remove(kTrain);
  std::remove("ft_test_model.bin");
  std::printf("test fasttext 0.9.2: OK\n");
  return 0;
}