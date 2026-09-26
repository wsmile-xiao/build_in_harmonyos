/* test_package/test_libheif_openjpeg.c — libheif-openjpeg 1.23.0 消费者测试（鸿蒙特有）
 *
 * R34：真实调用被测包交付面的 API，不是空壳测试。本包交付面 =
 *   * libheif 宿主（lib/libheif.so，ENABLE_PLUGIN_LOADING=ON）
 *   * OpenJPEG(JPEG 2000) 解码插件模块 lib/libheif/libheif-j2kdec.so（上游目标 heif-j2kdec）
 *   * OpenJPEG(JPEG 2000) 编码插件模块 lib/libheif/libheif-j2kenc.so（上游目标 heif-j2kenc）
 *
 * 插件是运行期由宿主 dlopen 的 MODULE，所以判据不是"能链接"，而是：
 *   ① 插件真被宿主装载并注册 JPEG 2000 编解码器
 *      （heif_init() → heif_get_plugin_directories() → heif_have_{decoder,encoder}_for_format）；
 *   ② 交付的 OpenJPEG 后端真能干活——做一次 J2K 编码 → 写文件 → 读回 → 解码的**真实往返**。
 *      父 tarball 内没有 J2K 语料，往返是唯一能同时覆盖 encoder 与 decoder 两个插件的验证。
 *      保真度判据取 **YCbCr 4:2:0 平面**（不掺 RGB↔YCbCr 色彩转换与色度子采样的额外损失，
 *      上游 tests/region.cc 等也用这一形态）：lossless 编码应当近似逐像素相等，
 *      设备实测 MAE 0.0395 / max 4（`$TASK_DIR/rtprobe/rt_probe2.c`），阈值取 MAE<=1、max<=16。
 *      另做一次 RGB 解码作结构判据（尺寸 + 平面可读），不设保真度阈值。
 *
 * 检查数与结果由程序自报（LIBSHEIF_OPENJPEG_CONSUMER checks_total=… checks_passed=…），
 * conanfile.py 不硬编码数字；任一检查失败即返回 1，conan create 判 FAIL。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libheif/heif.h>

#define RT_WIDTH 64
#define RT_HEIGHT 48

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

/* 平滑渐变的 YCbCr 4:2:0 测试图（色度平面按 2x2 采样取值） */
static unsigned char y_value(int x, int y) { return (unsigned char)((x * 2 + y) & 0xff); }
static unsigned char cb_value(int x, int y) { return (unsigned char)((96 + x / 4) & 0xff); }
static unsigned char cr_value(int x, int y) { return (unsigned char)((160 - y / 4) & 0xff); }

static int abs_diff(int a, int b) { return a > b ? a - b : b - a; }

int main(void)
{
  heif_error err;
  printf("libheif-openjpeg 1.23.0 consumer test\n");

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
  err = heif_init(NULL);
  printf("  heif_init(NULL) -> code=%d (%s)\n", (int)err.code,
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

  /* --- 4. 核心判据：两个 OpenJPEG 插件模块都已装载并注册 JPEG 2000 编解码器 --- */
  check(heif_have_decoder_for_format(heif_compression_JPEG2000) == 1,
        "heif_have_decoder_for_format(JPEG2000) == 1（libheif-j2kdec.so 已装载）");
  check(heif_have_encoder_for_format(heif_compression_JPEG2000) == 1,
        "heif_have_encoder_for_format(JPEG2000) == 1（libheif-j2kenc.so 已装载）");

  /* --- 5. 反证：本包未启用其它后端（交付面裁剪正确，插件不是"顺带被系统库命中"） --- */
  check(heif_have_decoder_for_format(heif_compression_HEVC) == 0,
        "decoder(HEVC) == 0（无 libde265/HEVC 后端）");
  check(heif_have_decoder_for_format(heif_compression_AV1) == 0,
        "decoder(AV1) == 0（无 AV1 后端）");
  check(heif_have_encoder_for_format(heif_compression_HEVC) == 0,
        "encoder(HEVC) == 0（无 HEVC 编码后端）");

  /* --- 6. 真实往返：YCbCr 4:2:0 lossless 编码 → 写文件 → 读回 → 解码 → 逐平面比对 --- */
  heif_image* img = NULL;
  err = heif_image_create(RT_WIDTH, RT_HEIGHT, heif_colorspace_YCbCr, heif_chroma_420, &img);
  check(err.code == heif_error_Ok && img != NULL, "heif_image_create(YCbCr 4:2:0) == Ok");
  err = heif_image_add_plane(img, heif_channel_Y, RT_WIDTH, RT_HEIGHT, 8);
  check(err.code == heif_error_Ok, "heif_image_add_plane(Y, 8bit) == Ok");
  err = heif_image_add_plane(img, heif_channel_Cb, (RT_WIDTH + 1) / 2, (RT_HEIGHT + 1) / 2, 8);
  check(err.code == heif_error_Ok, "heif_image_add_plane(Cb, 8bit) == Ok");
  err = heif_image_add_plane(img, heif_channel_Cr, (RT_WIDTH + 1) / 2, (RT_HEIGHT + 1) / 2, 8);
  check(err.code == heif_error_Ok, "heif_image_add_plane(Cr, 8bit) == Ok");

  int s_y = 0, s_c = 0;
  unsigned char* p_y = (unsigned char*)heif_image_get_plane(img, heif_channel_Y, &s_y);
  unsigned char* p_cb = (unsigned char*)heif_image_get_plane(img, heif_channel_Cb, &s_c);
  unsigned char* p_cr = (unsigned char*)heif_image_get_plane(img, heif_channel_Cr, &s_c);
  check(p_y != NULL && s_y >= RT_WIDTH, "heif_image_get_plane(Y) 可写");
  check(p_cb != NULL, "heif_image_get_plane(Cb) 可写");
  check(p_cr != NULL, "heif_image_get_plane(Cr) 可写");
  if (p_y != NULL && p_cb != NULL && p_cr != NULL) {
    for (int y = 0; y < RT_HEIGHT; y++) {
      for (int x = 0; x < RT_WIDTH; x++) {
        p_y[y * s_y + x] = y_value(x, y);
      }
    }
    for (int y = 0; y < (RT_HEIGHT + 1) / 2; y++) {
      for (int x = 0; x < (RT_WIDTH + 1) / 2; x++) {
        p_cb[y * s_c + x] = cb_value(x * 2, y * 2);
        p_cr[y * s_c + x] = cr_value(x * 2, y * 2);
      }
    }
  }

  const char* out_path = "roundtrip_j2k.heif";
  remove(out_path);

  heif_context* enc_ctx = heif_context_alloc();
  heif_encoder* encoder = NULL;
  err = heif_context_get_encoder_for_format(enc_ctx, heif_compression_JPEG2000, &encoder);
  check(err.code == heif_error_Ok && encoder != NULL,
        "heif_context_get_encoder_for_format(JPEG2000) == Ok");
  if (encoder != NULL) {
    err = heif_encoder_set_lossless(encoder, 1);
    check(err.code == heif_error_Ok, "heif_encoder_set_lossless(1) == Ok");

    heif_image_handle* out_handle = NULL;
    err = heif_context_encode_image(enc_ctx, img, encoder, NULL, &out_handle);
    printf("  heif_context_encode_image(JPEG2000) -> code=%d (%s)\n", (int)err.code,
           err.message ? err.message : "");
    check(err.code == heif_error_Ok && out_handle != NULL,
          "heif_context_encode_image(JPEG2000) == Ok（编码插件真在干活）");
    if (out_handle != NULL) {
      err = heif_context_write_to_file(enc_ctx, out_path);
      check(err.code == heif_error_Ok, "heif_context_write_to_file() == Ok");
      heif_image_handle_release(out_handle);
    }
    heif_encoder_release(encoder);
  }
  heif_context_free(enc_ctx);

  FILE* written = fopen(out_path, "rb");
  long written_size = 0;
  if (written != NULL) {
    fseek(written, 0, SEEK_END);
    written_size = ftell(written);
    fclose(written);
  }
  printf("  %s = %ld bytes\n", out_path, written_size);
  check(written_size > 0, "J2K 编码输出文件非空");

  heif_context* dec_ctx = heif_context_alloc();
  err = heif_context_read_from_file(dec_ctx, out_path, NULL);
  check(err.code == heif_error_Ok, "heif_context_read_from_file(自产 J2K) == Ok");

  heif_image_handle* in_handle = NULL;
  err = heif_context_get_primary_image_handle(dec_ctx, &in_handle);
  check(err.code == heif_error_Ok && in_handle != NULL,
        "heif_context_get_primary_image_handle() == Ok");
  if (in_handle != NULL) {
    printf("  ispe = %dx%d\n", heif_image_handle_get_ispe_width(in_handle),
           heif_image_handle_get_ispe_height(in_handle));
    check(heif_image_handle_get_ispe_width(in_handle) == RT_WIDTH &&
              heif_image_handle_get_ispe_height(in_handle) == RT_HEIGHT,
          "ispe 尺寸 == 64x48（容器层元数据保真）");

    /* 6a. 解码回 YCbCr 4:2:0 并逐平面比对（lossless ⇒ 近似逐像素相等） */
    heif_image* decoded = NULL;
    err = heif_decode_image(in_handle, &decoded, heif_colorspace_YCbCr, heif_chroma_420, NULL);
    printf("  heif_decode_image(YCbCr 4:2:0) -> code=%d (%s)\n", (int)err.code,
           err.message ? err.message : "");
    check(err.code == heif_error_Ok && decoded != NULL,
          "heif_decode_image(YCbCr 4:2:0) == Ok（解码插件真在干活）");
    if (decoded != NULL) {
      int o_y = 0, o_c = 0;
      const unsigned char* q_y = heif_image_get_plane_readonly(decoded, heif_channel_Y, &o_y);
      const unsigned char* q_cb = heif_image_get_plane_readonly(decoded, heif_channel_Cb, &o_c);
      const unsigned char* q_cr = heif_image_get_plane_readonly(decoded, heif_channel_Cr, &o_c);
      check(q_y != NULL, "解码后 Y 平面可读");
      check(q_cb != NULL, "解码后 Cb 平面可读");
      check(q_cr != NULL, "解码后 Cr 平面可读");
      if (q_y != NULL && q_cb != NULL && q_cr != NULL) {
        long long abs_sum = 0;
        long long samples = 0;
        int max_diff = 0;
        for (int y = 0; y < RT_HEIGHT; y++) {
          for (int x = 0; x < RT_WIDTH; x++) {
            int diff = abs_diff(q_y[y * o_y + x], y_value(x, y));
            abs_sum += diff; samples++;
            if (diff > max_diff) max_diff = diff;
          }
        }
        for (int y = 0; y < (RT_HEIGHT + 1) / 2; y++) {
          for (int x = 0; x < (RT_WIDTH + 1) / 2; x++) {
            int d_cb = abs_diff(q_cb[y * o_c + x], cb_value(x * 2, y * 2));
            int d_cr = abs_diff(q_cr[y * o_c + x], cr_value(x * 2, y * 2));
            abs_sum += d_cb + d_cr; samples += 2;
            if (d_cb > max_diff) max_diff = d_cb;
            if (d_cr > max_diff) max_diff = d_cr;
          }
        }
        double mae = (double)abs_sum / (double)samples;
        printf("  J2K lossless 往返保真度: MAE=%.4f max=%d（%lld 个样本，阈值 MAE<=1 max<=16）\n",
               mae, max_diff, samples);
        check(mae <= 1.0, "往返 MAE <= 1.0");
        check(max_diff <= 16, "往返单点最大误差 <= 16");
      }
      heif_image_release(decoded);
    }

    /* 6b. 结构判据：RGB 消费路径也能解码出正确尺寸的平面（不设保真度阈值） */
    heif_image* rgb = NULL;
    err = heif_decode_image(in_handle, &rgb, heif_colorspace_RGB,
                            heif_chroma_interleaved_RGB, NULL);
    check(err.code == heif_error_Ok && rgb != NULL, "heif_decode_image(RGB) == Ok");
    if (rgb != NULL) {
      int o_rgb = 0;
      const unsigned char* q_rgb =
          heif_image_get_plane_readonly(rgb, heif_channel_interleaved, &o_rgb);
      check(q_rgb != NULL, "RGB 交织平面可读");
      check(heif_image_get_width(rgb, heif_channel_interleaved) == RT_WIDTH &&
                heif_image_get_height(rgb, heif_channel_interleaved) == RT_HEIGHT,
            "RGB 解码尺寸 == 64x48");
      heif_image_release(rgb);
    }
    heif_image_handle_release(in_handle);
  }
  heif_context_free(dec_ctx);
  heif_image_release(img);
  remove(out_path);

  /* --- 7. 宿主 API 可用性：context 生命周期 --- */
  heif_context* ctx = heif_context_alloc();
  check(ctx != NULL, "heif_context_alloc() != NULL");
  if (ctx != NULL) {
    heif_context_free(ctx);
  }

  /* --- 8. 反初始化（与 heif_init 引用计数配对） --- */
  heif_deinit();

  printf("LIBSHEIF_OPENJPEG_CONSUMER checks_total=%d checks_passed=%d\n",
         checks_total, checks_passed);
  if (checks_passed != checks_total) {
    printf("RESULT: FAIL\n");
    return 1;
  }
  printf("RESULT: PASS\n");
  return 0;
}
