// 上游 tests/fuzzer/imageio_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 Decode()。
// 格式选择:WebP 阅读器(所有种子)/PNM 阅读器(P6 魔数种子)/
// WebPGuessImageReader 猜型(仅 RIFF-WEBP 魔数种子——上游 Decode 对
// 猜型失败(NULL 阅读器)无防护,这与上游在启用全部阅读器时的行为一致)。
#include "driver_common.h"

#include "imageio_fuzzer.cc"

static bool HasP6Magic(const std::string& s) {
  return s.size() >= 3 && s[0] == 'P' && s[1] == '6';
}

int main(int argc, char** argv) {
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  int runs = 0;
  for (const std::string& s : seeds) {
    const std::string_view sv(s.data(), s.size());
    Decode(sv, WEBP_WEBP_FORMAT, /*keep_alpha=*/false, /*use_argb=*/false);
    Decode(sv, WEBP_WEBP_FORMAT, /*keep_alpha=*/true, /*use_argb=*/true);
    ++runs;
    if (HasWebPMagic(s)) {
      Decode(sv, kUnknown, /*keep_alpha=*/true, /*use_argb=*/false);
      ++runs;
    }
    if (HasP6Magic(s)) {
      Decode(sv, WEBP_PNM_FORMAT, /*keep_alpha=*/true, /*use_argb=*/false);
      ++runs;
    }
  }

  SeedSanity(seeds);
  printf("PASS imageio_fuzzer runs=%d\n", runs);
  return 0;
}
