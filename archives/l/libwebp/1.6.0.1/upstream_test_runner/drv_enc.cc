// 上游 tests/fuzzer/enc_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 EncTest()。
// 配置:三档 WebPConfig(无损 m6 q100 / 有损 m4 q75 / 有损 m0 q50)×
//       use_argb 0/1 × optimization 0/4;裁剪缩放参数关闭(alter_input=false)。
// 种子:仅 RIFF-WEBP 魔数(上游 EncTest 对 WebPGuessImageReader 的 NULL
//       阅读器无防护,与上游默认全部阅读器可用时的语义一致)。
#include "driver_common.h"

#include "enc_fuzzer.cc"

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
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  fuzz_utils::CropOrScaleParams params;
  memset(&params, 0, sizeof(params));  // alter_input=false → 不做裁剪缩放

  int runs = 0;
  for (const std::string& s : seeds) {
    if (!HasWebPMagic(s)) continue;
    const std::string_view sv(s.data(), s.size());
    for (int cfg_i = 0; cfg_i < 3; ++cfg_i) {
      const WebPConfig cfg =
          (cfg_i == 0)   ? MakeConfig(/*lossless=*/1, 100.f, /*method=*/6)
          : (cfg_i == 1) ? MakeConfig(/*lossless=*/0, 75.f, /*method=*/4)
                         : MakeConfig(/*lossless=*/0, 50.f, /*method=*/0);
      for (int use_argb = 0; use_argb <= 1; ++use_argb) {
        EncTest(sv, /*optimization_index=*/0, use_argb != 0, cfg, params);
        EncTest(sv, /*optimization_index=*/4, use_argb != 0, cfg, params);
        ++runs;
      }
    }
  }

  SeedSanity(seeds);
  printf("PASS enc_fuzzer runs=%d\n", runs);
  return 0;
}
