// 上游 tests/fuzzer/animencoder_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 AnimEncoderTest()。
// 帧序列:3 帧(内置源图 0/1/2,无损+有损混排,时间戳 30ms);
// 组合:minimize_size {0,1} × allow_mixed {0,1} × kmin/kmax {2/4, 3/6}
//       × optimization {0,4}。
#include "driver_common.h"

#include "animencoder_fuzzer.cc"

int main(int argc, char** argv) {
  std::vector<std::string> seeds;  // 本目标无需外部种子(blob 仅作位源)
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  fuzz_utils::CropOrScaleParams params;
  memset(&params, 0, sizeof(params));  // alter_input=false → 不做裁剪缩放

  WebPConfig cfg_lossless;
  WebPConfigInit(&cfg_lossless);
  cfg_lossless.lossless = 1;
  cfg_lossless.quality = 100.f;
  cfg_lossless.method = 4;
  cfg_lossless.alpha_quality = 100;
  cfg_lossless.exact = 1;

  WebPConfig cfg_lossy;
  WebPConfigInit(&cfg_lossy);
  cfg_lossy.lossless = 0;
  cfg_lossy.quality = 75.f;
  cfg_lossy.method = 4;
  cfg_lossy.alpha_quality = 100;
  cfg_lossy.exact = 1;

  // FrameConfig 字段序:int use_argb; int timestamp; WebPConfig webp_config;
  //                   CropOrScaleParams; int source_image_index
  std::vector<FrameConfig> frames;
  frames.push_back(FrameConfig{0, 30, cfg_lossless, params, 0});
  frames.push_back(FrameConfig{1, 30, cfg_lossy, params, 1});
  frames.push_back(FrameConfig{0, 30, cfg_lossy, params, 2});

  int runs = 0;
  for (int minimize = 0; minimize <= 1; ++minimize) {
    for (int mixed = 0; mixed <= 1; ++mixed) {
      AnimEncoderTest(std::string_view("", 0), minimize != 0,
                      std::make_pair(2, 4), mixed != 0, frames,
                      /*optimization_index=*/0);
      AnimEncoderTest(std::string_view("", 0), minimize != 0,
                      std::make_pair(3, 6), mixed != 0, frames,
                      /*optimization_index=*/4);
      runs += 2;
    }
  }

  printf("PASS animencoder_fuzzer runs=%d\n", runs);
  return 0;
}
