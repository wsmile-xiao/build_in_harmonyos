/* test_package/test_libheif_aom.c — libheif-aom 1.23.0 消费者测试（鸿蒙特有）
 *
 * R34：真实调用被测包交付面的 API，不是空壳测试。
 *
 * 本包交付面 = libheif 宿主（lib/libheif.so）+ **两个** aom（AV1）插件模块
 * （lib/libheif/libheif-aomdec.so、lib/libheif/libheif-aomenc.so，上游目标
 * heif-aomdec / heif-aomenc）。插件是运行期由宿主 dlopen 的 MODULE，所以判据不能
 * 停在"能链接"，必须证明插件真被宿主装载并注册了 AV1 后端，而且真的能编能解：
 *
 *   1) 版本指纹 = 1.23.0（链接到的宿主就是本包交付的那一份）；
 *   2) heif_init() → heif_get_plugin_directories() 指向 <pkg>/lib/libheif
 *      （配方 package_info() 的 runenv_info 经 LIBHEIF_PLUGIN_PATH 带出）；
 *   3) heif_have_decoder_for_format(AV1) == 1 且 heif_have_encoder_for_format(AV1) == 1
 *      （两个插件模块都被装载并注册）；
 *   4) 反证：HEVC 解码/编码后端均为 0（本包未启用其它后端）；
 *   5) **端到端功能**：用交付的 aomenc 插件把一张合成 YCbCr 4:2:0 图编成 AV1/HEIF
 *      （内存内，不落盘），再用交付的 aomdec 插件读回并解码，校验尺寸与像素误差
 *      ——证明插件不只是"注册上了"，而是真的能工作。
 *
 * 检查数与结果由程序自报（LIBHEIF_AOM_CONSUMER checks_total=… checks_passed=…），
 * conanfile.py 不硬编码数字；任一检查失败即返回 1，conan create 判 FAIL。
 * 全部数据在内存中构造，不依赖任何外部测试文件（提交面不含二进制夹具）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libheif/heif.h>

#define TEST_W 64
#define TEST_H 64

static int checks_total = 0;
static int checks_passed = 0;

static void check(int condition, const char* what)
{
  checks_total++;
  if (condition) {
    checks_passed++;
    printf("  [ ok ] %s\n", what);
  }
  else {
    printf("  [FAIL] %s\n", what);
  }
}

/* ---------------------------------------------------------------- 内存写入器 */

struct membuf
{
  unsigned char* data;
  size_t size;
  size_t cap;
};

static heif_error membuf_write(heif_context* ctx, const void* data, size_t size,
                               void* userdata)
{
  (void) ctx;
  struct membuf* b = (struct membuf*) userdata;
  heif_error err;
  err.code = heif_error_Ok;
  err.subcode = heif_suberror_Unspecified;
  err.message = "ok";

  if (b->size + size > b->cap) {
    size_t ncap = (b->size + size) * 2 + 4096;
    unsigned char* nd = (unsigned char*) realloc(b->data, ncap);
    if (nd == NULL) {
      err.code = heif_error_Encoding_error;
      err.message = "out of memory";
      return err;
    }
    b->data = nd;
    b->cap = ncap;
  }
  memcpy(b->data + b->size, data, size);
  b->size += size;
  return err;
}

/* ---------------------------------------------------------------- 合成测试图 */

/* 平滑渐变 Y 平面 + 中性色度：AV1 有损编码后仍能逐点比对（容差见下）。 */
static int fill_test_image(heif_image* img)
{
  int ystride = 0, cstride = 0;
  uint8_t* y = heif_image_get_plane(img, heif_channel_Y, &ystride);
  uint8_t* cb = heif_image_get_plane(img, heif_channel_Cb, &cstride);
  uint8_t* cr = heif_image_get_plane(img, heif_channel_Cr, &cstride);
  if (y == NULL || cb == NULL || cr == NULL) {
    return 0;
  }
  for (int row = 0; row < TEST_H; row++) {
    for (int col = 0; col < TEST_W; col++) {
      y[row * ystride + col] = (uint8_t) ((col * 2 + row * 2) & 0xFF);
    }
  }
  for (int row = 0; row < (TEST_H + 1) / 2; row++) {
    for (int col = 0; col < (TEST_W + 1) / 2; col++) {
      cb[row * cstride + col] = 128;
      cr[row * cstride + col] = 128;
    }
  }
  return 1;
}

int main(void)
{
  printf("libheif-aom 1.23.0 consumer test\n");

  /* --- 1. 版本指纹：链接到的宿主必须就是本包交付的 1.23.0 --- */
  const char* version = heif_get_version();
  printf("  heif_get_version() = %s\n", version ? version : "(null)");
  check(version != NULL && strcmp(version, "1.23.0") == 0,
        "heif_get_version() == \"1.23.0\"");
  check(heif_get_version_number_major() == 1 &&
            heif_get_version_number_minor() == 23 &&
            heif_get_version_number_maintenance() == 0,
        "heif_get_version_number_major/minor/maintenance == 1/23/0");

  /* --- 2. 初始化：上游文档明确 heif_init() 才装载默认插件目录下的外部插件 --- */
  heif_error err = heif_init(NULL);
  printf("  heif_init(NULL) -> code=%d (%s)\n", (int) err.code,
         err.message ? err.message : "");
  check(err.code == heif_error_Ok, "heif_init(NULL) == heif_error_Ok");

  /* --- 3. 插件搜索目录：由配方 package_info() 的 runenv_info 经
   *        LIBHEIF_PLUGIN_PATH 导出（上游 plugins_unix.cc 优先读它） --- */
  const char* const* dirs = heif_get_plugin_directories();
  int dir_count = 0;
  int dir_is_package_libheif = 0;
  if (dirs != NULL) {
    for (int i = 0; dirs[i] != NULL; i++) {
      dir_count++;
      printf("  plugin dir[%d] = %s\n", i, dirs[i]);
      if (strstr(dirs[i], "libheif") != NULL) {
        dir_is_package_libheif = 1;
      }
    }
  }
  check(dir_count >= 1, "heif_get_plugin_directories() 返回 >= 1 个插件目录");
  check(dir_is_package_libheif == 1,
        "插件目录指向交付的 <pkg>/lib/libheif（LIBHEIF_PLUGIN_PATH 生效）");

  /* --- 4. 核心判据：两个 aom 插件模块都已装载并注册 AV1 后端 --- */
  check(heif_have_decoder_for_format(heif_compression_AV1) == 1,
        "heif_have_decoder_for_format(AV1) == 1（libheif-aomdec.so 已装载）");
  check(heif_have_encoder_for_format(heif_compression_AV1) == 1,
        "heif_have_encoder_for_format(AV1) == 1（libheif-aomenc.so 已装载）");

  /* --- 5. 反证：本包未启用其它后端 --- */
  check(heif_have_decoder_for_format(heif_compression_HEVC) == 0,
        "heif_have_decoder_for_format(HEVC) == 0（无 HEVC 后端）");
  check(heif_have_encoder_for_format(heif_compression_HEVC) == 0,
        "heif_have_encoder_for_format(HEVC) == 0（无 HEVC 后端）");

  /* --- 6. 端到端：交付的 aomenc 插件编码 → 内存 → 交付的 aomdec 插件解码 --- */
  heif_context* enc_ctx = heif_context_alloc();
  check(enc_ctx != NULL, "heif_context_alloc() != NULL");

  heif_encoder* enc = NULL;
  err = heif_context_get_encoder_for_format(enc_ctx, heif_compression_AV1, &enc);
  printf("  heif_context_get_encoder_for_format(AV1) -> code=%d (%s)\n",
         (int) err.code, err.message ? err.message : "");
  check(err.code == heif_error_Ok && enc != NULL,
        "取得 AV1 编码器（来自交付的 libheif-aomenc.so）");

  heif_image* img = NULL;
  check(heif_image_create(TEST_W, TEST_H, heif_colorspace_YCbCr, heif_chroma_420,
                          &img).code == heif_error_Ok && img != NULL,
        "heif_image_create(YCbCr 4:2:0) 成功");
  check(heif_image_add_plane(img, heif_channel_Y, TEST_W, TEST_H, 8).code ==
            heif_error_Ok &&
            heif_image_add_plane(img, heif_channel_Cb, (TEST_W + 1) / 2,
                                 (TEST_H + 1) / 2, 8).code == heif_error_Ok &&
            heif_image_add_plane(img, heif_channel_Cr, (TEST_W + 1) / 2,
                                 (TEST_H + 1) / 2, 8).code == heif_error_Ok,
        "heif_image_add_plane(Y/Cb/Cr) 成功");
  check(fill_test_image(img) == 1, "合成测试图（Y 渐变 + 中性色度）写入成功");

  if (enc != NULL) {
    heif_encoder_set_lossy_quality(enc, 90);
  }
  heif_image_handle* enc_handle = NULL;
  err = heif_context_encode_image(enc_ctx, img, enc, NULL, &enc_handle);
  printf("  heif_context_encode_image(AV1) -> code=%d (%s)\n", (int) err.code,
         err.message ? err.message : "");
  check(err.code == heif_error_Ok && enc_handle != NULL,
        "heif_context_encode_image 用 aom 编码成功");

  struct membuf buf;
  buf.data = NULL;
  buf.size = 0;
  buf.cap = 0;
  heif_writer writer;
  writer.writer_api_version = 1;
  writer.write = membuf_write;
  err = heif_context_write(enc_ctx, &writer, &buf);
  printf("  heif_context_write -> code=%d, bytes=%lu\n", (int) err.code,
         (unsigned long) buf.size);
  check(err.code == heif_error_Ok && buf.size > 0, "编码结果写出到内存成功");
  check(buf.size > 16 && buf.data != NULL && memcmp(buf.data + 4, "ftyp", 4) == 0,
        "输出是 ISO-BMFF（偏移 4 起为 'ftyp' box）");

  heif_context* dec_ctx = heif_context_alloc();
  err = heif_context_read_from_memory_without_copy(dec_ctx, buf.data, buf.size, NULL);
  printf("  heif_context_read_from_memory_without_copy -> code=%d (%s)\n",
         (int) err.code, err.message ? err.message : "");
  check(err.code == heif_error_Ok, "读回内存中的 HEIF 数据成功");

  heif_image_handle* dec_handle = NULL;
  err = heif_context_get_primary_image_handle(dec_ctx, &dec_handle);
  check(err.code == heif_error_Ok && dec_handle != NULL, "取得主图句柄");
  check(dec_handle != NULL && heif_image_handle_get_width(dec_handle) == TEST_W &&
            heif_image_handle_get_height(dec_handle) == TEST_H,
        "解码句柄尺寸 == 64x64");

  heif_image* out = NULL;
  err = heif_decode_image(dec_handle, &out, heif_colorspace_YCbCr, heif_chroma_420, NULL);
  printf("  heif_decode_image(AV1) -> code=%d (%s)\n", (int) err.code,
         err.message ? err.message : "");
  check(err.code == heif_error_Ok && out != NULL,
        "heif_decode_image 用 aom 解码成功");

  if (out != NULL) {
    int stride = 0;
    uint8_t* y = heif_image_get_plane(out, heif_channel_Y, &stride);
    check(y != NULL && stride > 0 && heif_image_get_width(out, heif_channel_Y) == TEST_W &&
              heif_image_get_height(out, heif_channel_Y) == TEST_H,
          "解码图 Y 平面尺寸 == 64x64");

    if (y != NULL) {
      long long sum_abs = 0;
      int max_abs = 0;
      int samples = 0;
      for (int row = 0; row < TEST_H; row++) {
        for (int col = 0; col < TEST_W; col++) {
          int expect = (col * 2 + row * 2) & 0xFF;
          int got = y[row * stride + col];
          int d = got - expect;
          if (d < 0) {
            d = -d;
          }
          if (d > max_abs) {
            max_abs = d;
          }
          sum_abs += d;
          samples++;
        }
      }
      double mean_abs = samples > 0 ? (double) sum_abs / (double) samples : 999.0;
      printf("  luma roundtrip: samples=%d mean_abs_diff=%.2f max_abs_diff=%d\n",
             samples, mean_abs, max_abs);
      check(samples == TEST_W * TEST_H, "逐点比对样本数 == 4096");
      check(mean_abs < 12.0, "有损往返平均绝对误差 < 12（AV1 q=90）");
      check(max_abs <= 48, "有损往返单点最大绝对误差 <= 48");
    }
    heif_image_release(out);
  }

  /* --- 7. 生命周期收尾（与 heif_init 引用计数配对） --- */
  if (dec_handle != NULL) {
    heif_image_handle_release(dec_handle);
  }
  heif_context_free(dec_ctx);
  if (enc_handle != NULL) {
    heif_image_handle_release(enc_handle);
  }
  if (enc != NULL) {
    heif_encoder_release(enc);
  }
  if (img != NULL) {
    heif_image_release(img);
  }
  heif_context_free(enc_ctx);
  free(buf.data);
  heif_deinit();

  printf("LIBHEIF_AOM_CONSUMER checks_total=%d checks_passed=%d\n", checks_total,
         checks_passed);
  if (checks_passed != checks_total) {
    printf("RESULT: FAIL\n");
    return 1;
  }
  printf("RESULT: PASS\n");
  return 0;
}
