// test_package 消费者测试 — 真实调用 bioparser 公开 API
// 仅使用已安装包的公开头文件 (bioparser/*.hpp) 与公开 API，验证编译、链接、调用与可观察结果。
#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "bioparser/fasta_parser.hpp"
#include "bioparser/parser.hpp"

class Seq {
 public:
  Seq(const char* name, std::uint64_t name_len,
      const char* data, std::uint64_t data_len,
      const char* quality = nullptr, std::uint64_t quality_len = 0)
      : name(name, name_len), data(data, data_len),
        quality(quality ? std::string(quality, quality_len) : std::string()) {}
  std::string name;
  std::string data;
  std::string quality;
};

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "usage: test_bioparser <fasta_file>" << std::endl;
    return 2;
  }
  auto parser = bioparser::Parser<Seq>::Create<bioparser::FastaParser>(argv[1]);
  auto seqs = parser->Parse(1ULL << 62, true);
  if (seqs.empty()) {
    std::cerr << "FAIL: no sequences parsed" << std::endl;
    return 1;
  }
  std::uint64_t data_len = 0;
  for (const auto& s : seqs) {
    data_len += s->data.size();
  }
  std::cout << "OK parsed=" << seqs.size() << " data_len=" << data_len
            << " first=" << seqs.front()->name << std::endl;
  return 0;
}
