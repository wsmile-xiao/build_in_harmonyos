// Consumer test for tinydng 0.1.0 on HarmonyOS PC (aarch64).
//
// 真实 API 回环测试：tinydngwriter 写一张 16x16 RGB 16bit 的 DNG（像素值
// 确定性生成），再用 tinydng loader 读回，断言图像元数据与像素字节逐位
// 一致。任一断言失败返回非 0。
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#define TINY_DNG_WRITER_IMPLEMENTATION
#include "tiny_dng_writer.h"

#define STB_IMAGE_IMPLEMENTATION
#define TINY_DNG_LOADER_IMPLEMENTATION
#include "tiny_dng_loader.h"

namespace {

int g_failures = 0;

#define CHECK(cond)                                                     \
  do {                                                                  \
    if (!(cond)) {                                                      \
      ++g_failures;                                                     \
      std::cerr << "FAIL(line " << __LINE__ << "): " #cond << std::endl; \
    }                                                                   \
  } while (0)

}  // namespace

int main() {
  const unsigned int kWidth = 16;
  const unsigned int kHeight = 16;

  // 确定性像素：16bit RGB 交错
  std::vector<unsigned short> pixels(size_t(kWidth) * kHeight * 3);
  for (size_t i = 0; i < pixels.size(); ++i) {
    pixels[i] = static_cast<unsigned short>((i * 7919 + 12345) & 0xffffu);
  }

  // ---- 写入 ----
  {
    tinydngwriter::DNGImage img;
    img.SetBigEndian(false);  // little-endian DNG

    CHECK(img.SetImageWidth(kWidth));
    CHECK(img.SetImageLength(kHeight));
    // 上游不支持多 strip，RowsPerStrip 必须等于图像高度
    CHECK(img.SetRowsPerStrip(kHeight));
    CHECK(img.SetSamplesPerPixel(3));
    unsigned short bps[3] = {16, 16, 16};
    CHECK(img.SetBitsPerSample(3, bps));
    CHECK(img.SetPlanarConfig(tinydngwriter::PLANARCONFIG_CONTIG));
    CHECK(img.SetCompression(tinydngwriter::COMPRESSION_NONE));
    CHECK(img.SetPhotometric(tinydngwriter::PHOTOMETRIC_RGB));
    unsigned short sf[3] = {tinydngwriter::SAMPLEFORMAT_UINT,
                            tinydngwriter::SAMPLEFORMAT_UINT,
                            tinydngwriter::SAMPLEFORMAT_UINT};
    CHECK(img.SetSampleFormat(3, sf));
    CHECK(img.SetImageData(reinterpret_cast<const unsigned char*>(pixels.data()),
                           pixels.size() * sizeof(unsigned short)));

    tinydngwriter::DNGWriter writer(false);
    CHECK(writer.AddImage(&img));
    std::string err;
    const bool ok = writer.WriteToFile("tinydng_test_roundtrip.dng", &err);
    CHECK(ok);
    CHECK(err.empty());
    if (!ok) {
      std::cerr << "writer err: " << err << std::endl;
    }
  }

  // ---- 读回 ----
  {
    std::string warn, err;
    std::vector<tinydng::DNGImage> images;
    std::vector<tinydng::FieldInfo> custom_fields;
    const bool ret =
        tinydng::LoadDNG("tinydng_test_roundtrip.dng", custom_fields, &images, &warn, &err);
    CHECK(ret);
    if (!ret) {
      std::cerr << "loader warn: " << warn << " err: " << err << std::endl;
    } else {
      CHECK(images.size() == size_t(1));
      const tinydng::DNGImage& im = images[0];
      CHECK(im.width == int(kWidth));
      CHECK(im.height == int(kHeight));
      CHECK(im.bits_per_sample == 16);
      CHECK(im.samples_per_pixel == 3);
      CHECK(im.sample_format == 1);  // SAMPLEFORMAT_UINT
      const size_t expect_bytes = size_t(kWidth) * kHeight * 3 * sizeof(unsigned short);
      CHECK(im.data.size() == expect_bytes);
      if (im.data.size() == expect_bytes) {
        CHECK(std::memcmp(im.data.data(), pixels.data(), expect_bytes) == 0);
      }
    }
  }

  if (g_failures == 0) {
    std::cout << "test_tinydng: PASS" << std::endl;
    return 0;
  }
  std::cout << "test_tinydng: FAIL(" << g_failures << ")" << std::endl;
  return 1;
}
