// 上游 tests/fuzzer/advanced_api_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 AdvancedApiTest()。
// 组合:factor {0,128,255} × colorspace {RGBA,rgbA,YUV} × 三组选项采样
//       (全默认 / 全开+增量 / 裁剪缩放无抖动)。
#include "driver_common.h"

#include "advanced_api_fuzzer.cc"

int main(int argc, char** argv) {
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  static const int kColorspaces[] = {MODE_RGBA, MODE_rgbA, MODE_YUV};
  int runs = 0;
  for (const std::string& s : seeds) {
    const std::string_view sv(s.data(), s.size());
    for (int cs : kColorspaces) {
      // 全默认(仅 colorspace 变化)
      AdvancedApiTest(sv, /*factor_u8=*/128, /*flip=*/0,
                      /*bypass_filtering=*/0, /*no_fancy_upsampling=*/0,
                      /*use_threads=*/0, /*use_cropping=*/0,
                      /*use_scaling=*/0, /*use_dithering=*/0, cs,
                      /*incremental=*/0);
      // 全开 + 增量解码
      AdvancedApiTest(sv, /*factor_u8=*/255, /*flip=*/1,
                      /*bypass_filtering=*/1, /*no_fancy_upsampling=*/1,
                      /*use_threads=*/1, /*use_cropping=*/1,
                      /*use_scaling=*/1, /*use_dithering=*/1, cs,
                      /*incremental=*/1);
      // 裁剪+缩放、无抖动、无增量
      AdvancedApiTest(sv, /*factor_u8=*/0, /*flip=*/0,
                      /*bypass_filtering=*/0, /*no_fancy_upsampling=*/0,
                      /*use_threads=*/0, /*use_cropping=*/1,
                      /*use_scaling=*/1, /*use_dithering=*/0, cs,
                      /*incremental=*/0);
      runs += 3;
    }
  }

  SeedSanity(seeds);
  printf("PASS advanced_api_fuzzer runs=%d\n", runs);
  return 0;
}
