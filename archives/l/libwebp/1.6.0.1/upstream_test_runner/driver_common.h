// fuzzrun/driver_common.h — 12 个 fuzz 目标 driver 的公共工具。
//
// 每个 driver 的工作方式(上游源码零改动):
//   1. #include 上游 tests/fuzzer/xxx_fuzzer.cc,把其匿名命名空间内的被测函数
//      并入本 TU,使其可直接调用;
//   2. main() 读取种子文件(真实 WebP 流/损坏/随机/截断等),逐种子直接执行
//      上游被测函数;
//   3. 执行完毕打印 PASS 行;任何崩溃/abort = 非零退出 = FAIL。
#ifndef FUZZRUN_DRIVER_COMMON_H_
#define FUZZRUN_DRIVER_COMMON_H_

#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

#include "src/webp/decode.h"  // 种子自检用公共 API(-I 指向 libwebp 源码根)

static bool ReadFile(const char* path, std::string* out) {
  FILE* f = fopen(path, "rb");
  if (f == nullptr) return false;
  fseek(f, 0, SEEK_END);
  const long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  out->resize(static_cast<size_t>(n));
  size_t r = 0;
  if (n > 0) r = fread(&(*out)[0], 1, static_cast<size_t>(n), f);
  fclose(f);
  return r == static_cast<size_t>(n);
}

// 读取 argv[1..] 全部种子;无参数时退化为单条空种子(空输入也是合法 fuzz 输入)。
static int LoadSeeds(int argc, char** argv, std::vector<std::string>* seeds) {
  for (int i = 1; i < argc; ++i) {
    std::string s;
    if (!ReadFile(argv[i], &s)) {
      fprintf(stderr, "SEED-READ-FAIL %s\n", argv[i]);
      return 1;
    }
    seeds->push_back(std::move(s));
  }
  if (seeds->empty()) seeds->push_back(std::string());
  return 0;
}

static bool HasWebPMagic(const std::string& s);  // 定义见文件尾

// 种子自检:证明语料是真实可解析的 WebP 流(与 test_package 探针互为印证)。
// 仅打印不判失败——损坏/随机种子本就应该被被测函数安全拒绝。
// 动画种子在简单解码 API 下会被拒绝,由 features.has_animation 标记说明。
static void SeedSanity(const std::vector<std::string>& seeds) {
  for (size_t i = 0; i < seeds.size(); ++i) {
    const std::string& s = seeds[i];
    const char* magic =
        HasWebPMagic(s) ? "RIFF-WEBP" : (s.size() >= 3 && s[0] == 'P' && s[1] == '6')
                              ? "PPM(P6)" : "none";
    WebPBitstreamFeatures feat;
    memset(&feat, 0, sizeof(feat));
    const VP8StatusCode st = WebPGetFeatures(
        reinterpret_cast<const uint8_t*>(s.data()), s.size(), &feat);
    int w = 0, h = 0;
    uint8_t* buf = WebPDecodeRGBA(
        reinterpret_cast<const uint8_t*>(s.data()), s.size(), &w, &h);
    printf("[sanity] seed %zu (%zu bytes) magic=%s features=%s", i, s.size(),
           magic, st == VP8_STATUS_OK ? "OK" : "rejected");
    if (st == VP8_STATUS_OK)
      printf(" %dx%d%s", feat.width, feat.height,
             feat.has_animation ? " animated" : "");
    printf(" decodeRGBA=%s", buf != nullptr ? "OK" : "rejected/empty");
    printf("\n");
    WebPFree(buf);
  }
}

// RIFF....WEBP 魔数检查:供需要真实 WebP 流的 driver 过滤种子。
static bool HasWebPMagic(const std::string& s) {
  return s.size() >= 12 && memcmp(s.data(), "RIFF", 4) == 0 &&
         memcmp(s.data() + 8, "WEBP", 4) == 0;
}

#endif  // FUZZRUN_DRIVER_COMMON_H_
