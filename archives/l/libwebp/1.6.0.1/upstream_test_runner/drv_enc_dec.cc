// 上游 tests/fuzzer/enc_dec_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 EncDecTest()。
// 源图:内置三张上游测试图(kImgAlphaData/kImgGridData/kImgPeakData,
// 16x16,GetSourcePicture 导入);配置三档 × use_argb 0/1 × optimization 0/4。
#include "driver_common.h"

#include "enc_dec_fuzzer.cc"

static WebPConfig MakeConfig(int lossless, float q, int method) {
  WebPConfig cfg;
  WebPConfigInit(&cfg);
  cfg.lossless = lossless;
  cfg.quality = q;
  cfg.method = method;
  cfg.alpha_quality = 100;
  cfg.exact = 1;
  return cfg;
}

int main(int argc, char** argv) {
  std::vector<std::string> seeds;  // 本目标无需外部种子
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  fuzz_utils::CropOrScaleParams params;
  memset(&params, 0, sizeof(params));  // alter_input=false → 不做裁剪缩放

  int runs = 0;
  for (int img = 0; img < static_cast<int>(fuzz_utils::kNumSourceImages);
       ++img) {
    for (int use_argb = 0; use_argb <= 1; ++use_argb) {
      for (int cfg_i = 0; cfg_i < 3; ++cfg_i) {
        const WebPConfig cfg =
            (cfg_i == 0)   ? MakeConfig(/*lossless=*/1, 100.f, /*method=*/6)
            : (cfg_i == 1) ? MakeConfig(/*lossless=*/0, 75.f, /*method=*/4)
                           : MakeConfig(/*lossless=*/0, 50.f, /*method=*/0);
        EncDecTest(use_argb != 0, img, cfg, /*optimization_index=*/0, params);
        EncDecTest(use_argb != 0, img, cfg, /*optimization_index=*/4, params);
        runs += 2;
      }
    }
  }

  printf("PASS enc_dec_fuzzer runs=%d\n", runs);
  return 0;
}
