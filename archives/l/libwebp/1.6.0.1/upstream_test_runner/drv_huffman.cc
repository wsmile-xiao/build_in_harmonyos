// 上游 tests/fuzzer/huffman_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 HuffmanTest()。
// (HuffmanTest 直读位流内部 API:VP8LInitBitReader/VP8LReadBits/
//  ReadHuffmanCodesHelper 等内部符号由静态 libwebp 提供。)
#include "driver_common.h"

#include "huffman_fuzzer.cc"

int main(int argc, char** argv) {
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  int runs = 0;
  for (const std::string& s : seeds) {
    HuffmanTest(std::string_view(s.data(), s.size()));
    ++runs;
  }

  SeedSanity(seeds);
  printf("PASS huffman_fuzzer runs=%d\n", runs);
  return 0;
}
