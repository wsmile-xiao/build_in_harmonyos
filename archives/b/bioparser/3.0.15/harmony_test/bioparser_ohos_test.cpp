// Copyright (c) 2026 HarmonyOS adaptation
// HarmonyOS 专项测试：验证 bioparser 公开 API 在 OHOS aarch64 上可编译、链接、运行并产生可观察结果。
// 只使用官方公开头文件 include/bioparser/*.hpp 与公开 API（Parser::Create / Parse / Reset）。
// 与上游 gtest 用例独立：自定义轻量 Sequence 类型（仅满足公开模板参数约束），
// 解析真实 FASTA 数据并断言可观察结果（序列条数、名称长度、碱基总量、压缩文件路径）。

#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "bioparser/fasta_parser.hpp"
#include "bioparser/fastq_parser.hpp"
#include "bioparser/parser.hpp"

// 消费者自定义 Sequence 类型：与 biosoup::Sequence 同构（name/data 构造），
// 仅依赖 bioparser 公开模板约束，不包含库内部头文件。
class Sequence {
 public:
  Sequence(const char* name, std::uint64_t name_len,
           const char* data, std::uint64_t data_len,
           const char* quality = nullptr, std::uint64_t quality_len = 0)
      : name(name, name_len), data(data, data_len),
        quality(quality ? std::string(quality, quality_len) : std::string()) {}

  std::string name;
  std::string data;
  std::string quality;
};

int main(int argc, char** argv) {
  if (argc < 3) {
    std::cerr << "usage: " << argv[0] << " <fasta|fastq> <path>" << std::endl;
    return 2;
  }
  const std::string fmt(argv[1]);
  const std::string path(argv[2]);

  try {
    if (fmt == "fasta") {
      auto parser = bioparser::Parser<Sequence>::Create<bioparser::FastaParser>(path);
      auto seqs = parser->Parse(1ULL << 62, true);
      if (seqs.size() != 14) {
        std::cerr << "FASTA sequence count mismatch: got " << seqs.size()
                  << ", expected 14" << std::endl;
        return 1;
      }
      std::uint64_t name_len = 0;
      std::uint64_t data_len = 0;
      for (const auto& s : seqs) {
        name_len += s->name.size();
        data_len += s->data.size();
      }
      // 上游固定断言：14 条序列，名称总长 65，碱基总量 109117
      if (name_len != 65 || data_len != 109117) {
        std::cerr << "FASTA content mismatch: name_len=" << name_len
                  << " (expected 65), data_len=" << data_len
                  << " (expected 109117)" << std::endl;
        return 1;
      }
      std::cout << "OK fasta sequences=" << seqs.size()
                << " name_len=" << name_len << " data_len=" << data_len
                << std::endl;
    } else if (fmt == "fastq") {
      auto parser = bioparser::Parser<Sequence>::Create<bioparser::FastqParser>(path);
      auto seqs = parser->Parse(1ULL << 62, true);
      if (seqs.empty()) {
        std::cerr << "FASTQ parse returned empty result" << std::endl;
        return 1;
      }
      std::cout << "OK fastq sequences=" << seqs.size()
                << " first_name=" << seqs.front()->name
                << " first_len=" << seqs.front()->data.size()
                << std::endl;
    } else {
      std::cerr << "unsupported format: " << fmt << std::endl;
      return 2;
    }
  } catch (const std::exception& e) {
    std::cerr << "bioparser exception: " << e.what() << std::endl;
    return 1;
  }
  return 0;
}
