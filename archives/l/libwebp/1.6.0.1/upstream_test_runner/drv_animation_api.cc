// 上游 tests/fuzzer/animation_api_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 AnimationApiTest()。
// 组合:threads {0,1} × 动画支持的 4 种色彩模式(与上游 WithDomains 一致)。
#include "driver_common.h"

#include "animation_api_fuzzer.cc"

int main(int argc, char** argv) {
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  static const WEBP_CSP_MODE kModes[] = {MODE_RGBA, MODE_BGRA, MODE_rgbA,
                                         MODE_bgrA};
  int runs = 0;
  for (const std::string& s : seeds) {
    const std::string_view sv(s.data(), s.size());
    for (WEBP_CSP_MODE mode : kModes) {
      AnimationApiTest(sv, /*use_threads=*/false, mode);
      AnimationApiTest(sv, /*use_threads=*/true, mode);
      runs += 2;
    }
  }

  SeedSanity(seeds);
  printf("PASS animation_api_fuzzer runs=%d\n", runs);
  return 0;
}
