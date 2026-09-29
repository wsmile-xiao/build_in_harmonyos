// 上游 tests/fuzzer/webp_info_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 WebPInfoTest()。
// (webp_info_fuzzer.cc 内部 #include "examples/webpinfo.c",其引用的
//  imageio 辅助函数由本驱动所在可执行目标的 imageio 源提供。)
#include "driver_common.h"

#include "webp_info_fuzzer.cc"

int main(int argc, char** argv) {
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  int runs = 0;
  for (const std::string& s : seeds) {
    WebPInfoTest(std::string_view(s.data(), s.size()));
    ++runs;
  }

  SeedSanity(seeds);
  printf("PASS webp_info_fuzzer runs=%d\n", runs);
  return 0;
}
