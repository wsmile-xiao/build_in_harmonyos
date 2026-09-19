// HarmonyOS 专项测试 — spoa 4.1.5 消费者视角真实 API 调用
// 验证: 库版本、AlignmentEngine 创建、POA 图构建、共识序列生成
// 编译: 基于 test_package 配方，消费者以 find_package(spoa) 使用
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

#include "spoa/spoa.hpp"

int main() {
  // 1. 库版本自检
  const std::string ver = spoa::Version();
  std::cout << "spoa Version(): " << ver << std::endl;
  assert(ver == "4.1.5");

  // 2. 创建局部比对引擎 (Smith-Waterman, 线性 gap)
  auto engine = spoa::AlignmentEngine::Create(
      spoa::AlignmentType::kSW, 5, -4, -8);

  // 3. 用真实序列构建 POA 图
  spoa::Graph graph;
  const std::vector<std::string> sequences = {
      "ATGGCGTAAATGCA", "ATGGCGTCAATGCA", "ATGGCGTCAAATGCA", "ATGGCGTAAATGA"};
  for (const auto& seq : sequences) {
    auto alignment = engine->Align(seq, graph);
    graph.AddAlignment(alignment, seq);
  }

  // 4. 生成共识序列并验证
  const std::string consensus = graph.GenerateConsensus();
  std::cout << "Consensus: " << consensus << std::endl;
  assert(!consensus.empty());
  assert(consensus.find("ATGGCGT") != std::string::npos);

  // 5. 生成多序列比对并验证行数
  const auto msa = graph.GenerateMultipleSequenceAlignment();
  assert(msa.size() == sequences.size());
  std::cout << "MSA rows: " << msa.size() << std::endl;
  for (const auto& row : msa) {
    std::cout << "  " << row << std::endl;
  }

  std::cout << "spoa HarmonyOS test: PASS (version=" << ver
            << ", consensus_len=" << consensus.size() << ")" << std::endl;
  return 0;
}
