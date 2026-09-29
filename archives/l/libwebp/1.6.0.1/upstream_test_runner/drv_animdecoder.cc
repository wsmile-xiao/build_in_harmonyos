// 上游 tests/fuzzer/animdecoder_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 AnimDecoderTest()。
#include "driver_common.h"

#include "animdecoder_fuzzer.cc"

int main(int argc, char** argv) {
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  int runs = 0;
  for (const std::string& s : seeds) {
    AnimDecoderTest(std::string_view(s.data(), s.size()));
    ++runs;
  }

  SeedSanity(seeds);
  printf("PASS animdecoder_fuzzer runs=%d\n", runs);
  return 0;
}
