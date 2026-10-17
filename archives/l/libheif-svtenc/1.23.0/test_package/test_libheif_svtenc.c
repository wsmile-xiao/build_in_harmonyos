/*
 * libheif-svtenc 1.23.0 — 消费者视角验证（鸿蒙设备真实运行）
 *
 * 验证的交付面：
 *   <pkg>/lib/libheif/libheif-svtenc.so  —— 上游 CMake 目标 heif-svtenc（SVT-AV1 编码插件模块）
 *   <pkg>/lib/libSvtAv1Enc.so*           —— 包内树构建的 SVT-AV1 运行时（插件 DT_NEEDED）
 *   <pkg>/lib/libheif.so                 —— 宿主（ENABLE_PLUGIN_LOADING=ON）
 *
 * 检查分三层，共 14 项（每项都打印可核对的一行）：
 *   ① 身份/环境：宿主版本指纹、插件目录来自本包 runenv_info 导出的 LIBHEIF_PLUGIN_PATH、
 *      交付的插件文件确实存在；
 *   ② 注册：heif_have_encoder_for_format(AV1)==1（证明宿主 dlopen 了 libheif-svtenc.so
 *      并由它注册了 AV1 编码器），并用 HEVC 编码器 / AV1 解码器作反证（本包未启用
 *      其它后端，必须为 0）；
 *   ③ 功能：真实走一遍 AV1 编码（heif_context_encode_image → heif_context_write_to_file），
 *      断言输出 HEIF/AVIF 文件非空——这一步真正进入 SVT-AV1 编码器，不是空壳调用。
 *
 * 环境变量 LIBHEIF_PLUGIN_PATH 与 LD_LIBRARY_PATH 由 test_package/conanfile.py 的
 * `self.run(..., env="conanrun")`（VirtualRunEnv）提供，与最终用户 `conan install` 后
 * 的运行环境一致。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <libheif/heif.h>

static int g_checks = 0;
static int g_failures = 0;

static void check(int condition, const char* what)
{
  g_checks++;
  if (condition) {
    printf("  [ok]   %s\n", what);
  }
  else {
    g_failures++;
    printf("  [FAIL] %s\n", what);
  }
  fflush(stdout);
}

static const char* err_text(const struct heif_error* err)
{
  static char buf[512];
  snprintf(buf, sizeof(buf), "%s (%d/%d)", err->message ? err->message : "?",
           err->code, err->subcode);
  return buf;
}

int main(void)
{
  printf("libheif-svtenc 1.23.0 consumer check\n");

  /* ---- ① 身份 / 环境 -------------------------------------------------- */
  const char* version = heif_get_version();
  printf("  heif_get_version() = %s\n", version ? version : "(null)");
  check(version != NULL && strcmp(version, "1.23.0") == 0,
        "host libheif version fingerprint is 1.23.0");

  struct heif_error err = heif_init(NULL);
  check(err.code == heif_error_Ok, "heif_init() succeeds (host loads plugins)");
  if (err.code != heif_error_Ok) {
    printf("  heif_init error: %s\n", err_text(&err));
  }

  const char* plugin_path = getenv("LIBHEIF_PLUGIN_PATH");
  printf("  LIBHEIF_PLUGIN_PATH = %s\n", plugin_path ? plugin_path : "(unset)");
  check(plugin_path != NULL && plugin_path[0] != '\0',
        "LIBHEIF_PLUGIN_PATH exported by this package (runenv_info)");

  char plugin_file[1024];
  plugin_file[0] = '\0';
  int plugin_file_ok = 0;
  if (plugin_path && plugin_path[0]) {
    snprintf(plugin_file, sizeof(plugin_file), "%s/libheif-svtenc.so", plugin_path);
    struct stat st;
    plugin_file_ok = (stat(plugin_file, &st) == 0) && S_ISREG(st.st_mode) && st.st_size > 0;
    printf("  delivered plugin: %s\n", plugin_file);
  }
  check(plugin_file_ok, "delivered artifact <plugin_path>/libheif-svtenc.so exists and is non-empty");

  /* ---- ② 插件注册 + 反证 --------------------------------------------- */
  int have_av1_encoder = heif_have_encoder_for_format(heif_compression_AV1);
  int have_av1_decoder = heif_have_decoder_for_format(heif_compression_AV1);
  int have_hevc_encoder = heif_have_encoder_for_format(heif_compression_HEVC);
  printf("  have_encoder(AV1)=%d have_decoder(AV1)=%d have_encoder(HEVC)=%d\n",
         have_av1_encoder, have_av1_decoder, have_hevc_encoder);
  check(have_av1_encoder == 1,
        "heif_have_encoder_for_format(AV1)==1 (libheif-svtenc.so loaded and registered)");
  check(have_av1_decoder == 0,
        "negative control: heif_have_decoder_for_format(AV1)==0 (no dav1d/aom in this package)");
  check(have_hevc_encoder == 0,
        "negative control: heif_have_encoder_for_format(HEVC)==0 (no x265 in this package)");

  /* ---- ③ 真实编码：进入 SVT-AV1 编码器 -------------------------------- */
  struct heif_image* image = NULL;
  err = heif_image_create(128, 128, heif_colorspace_RGB, heif_chroma_interleaved_RGB, &image);
  check(err.code == heif_error_Ok && image != NULL, "heif_image_create(128x128 RGB)");

  int plane_ok = 0;
  uint8_t* plane = NULL;
  int stride = 0;
  if (image) {
    err = heif_image_add_plane(image, heif_channel_interleaved, 128, 128, 8);
    if (err.code == heif_error_Ok) {
      plane = heif_image_get_plane(image, heif_channel_interleaved, &stride);
    }
    plane_ok = (plane != NULL) && (stride >= 128 * 3);
  }
  check(plane_ok, "heif_image_add_plane + heif_image_get_plane (interleaved RGB)");

  struct heif_context* ctx = heif_context_alloc();
  check(ctx != NULL, "heif_context_alloc()");
  if (!ctx) {
    printf("RESULT: %d/%d checks passed\n", g_checks - g_failures, g_checks);
    return 1;
  }

  struct heif_encoder* encoder = NULL;
  err = heif_context_get_encoder_for_format(ctx, heif_compression_AV1, &encoder);
  check(err.code == heif_error_Ok && encoder != NULL,
        "heif_context_get_encoder_for_format(AV1) returns the SVT-AV1 encoder");
  if (err.code != heif_error_Ok) {
    printf("  encoder error: %s\n", err_text(&err));
  }

  int encode_ok = 0;
  long output_size = 0;
  if (image && plane && encoder) {
    /* 填充可压缩但非平凡的渐变内容，避免全零图触发退化路径 */
    for (int y = 0; y < 128; y++) {
      for (int x = 0; x < 128; x++) {
        uint8_t* px = plane + y * stride + x * 3;
        px[0] = (uint8_t)((x * 2) & 0xFF);
        px[1] = (uint8_t)((y * 2) & 0xFF);
        px[2] = (uint8_t)((x + y) & 0xFF);
      }
    }

    err = heif_encoder_set_lossy_quality(encoder, 60);
    if (err.code != heif_error_Ok) {
      printf("  set_lossy_quality warning: %s\n", err_text(&err));
    }

    struct heif_image_handle* handle = NULL;
    err = heif_context_encode_image(ctx, image, encoder, NULL, &handle);
    if (err.code == heif_error_Ok && handle != NULL) {
      encode_ok = 1;
    }
    else {
      printf("  encode error: %s\n", err_text(&err));
    }

    if (handle) {
      const char* out = "libheif-svtenc-test.avif";
      err = heif_context_write_to_file(ctx, out);
      if (err.code == heif_error_Ok) {
        struct stat st;
        if (stat(out, &st) == 0) {
          output_size = (long)st.st_size;
        }
      }
      else {
        printf("  write error: %s\n", err_text(&err));
      }
      heif_image_handle_release(handle);
    }
  }
  printf("  encoded output size = %ld bytes\n", output_size);
  check(encode_ok, "heif_context_encode_image(AV1) through the SVT-AV1 plugin succeeds");
  check(output_size > 0, "encoded AVIF bitstream written to disk is non-empty");

  if (encoder) {
    heif_encoder_release(encoder);
  }
  heif_context_free(ctx);
  if (image) {
    heif_image_release(image);
  }

  /* heif_deinit() 返回 void（heif_library.h:148）；用"再 init 一次仍成功"证明生命周期闭合 */
  heif_deinit();
  err = heif_init(NULL);
  check(err.code == heif_error_Ok,
        "heif_deinit() then heif_init() again succeeds (reference-counted lifecycle)");
  heif_deinit();

  printf("RESULT: %d/%d checks passed\n", g_checks - g_failures, g_checks);
  return (g_failures == 0) ? 0 : 1;
}
