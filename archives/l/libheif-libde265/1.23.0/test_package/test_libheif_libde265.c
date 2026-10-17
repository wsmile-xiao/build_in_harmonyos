/* test_package/test_libheif_libde265.c — libheif-libde265 1.23.0 消费者测试（鸿蒙特有）
 *
 * R34：真实调用被测包交付面的 API，不是空壳测试。
 *
 * 本包交付面 = libheif 宿主（lib/libheif.so）+ libde265 解码插件模块
 * （lib/libheif/libheif-libde265.so，上游目标 heif-libde265）。插件是运行期由宿主
 * dlopen 的 MODULE，所以判据不是"能链接"，而是"插件真被宿主装载并注册了 HEVC 解码器"：
 *   heif_init() → heif_get_plugin_directories() → heif_have_decoder_for_format(HEVC)。
 *
 * 检查数与结果由程序自报（LIBSHEIF_LIBDE265_CONSUMER checks_total=… checks_passed=…），
 * conanfile.py 不硬编码数字；任一检查失败即返回 1，conan create 判 FAIL。
 */
#include <stdio.h>
#include <string.h>

#include <libheif/heif.h>

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

int main(void)
{
  printf("libheif-libde265 1.23.0 consumer test\n");

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

  /* --- 4. 核心判据：libde265 插件模块已装载并注册 HEVC 解码器 --- */
  check(heif_have_decoder_for_format(heif_compression_HEVC) == 1,
        "heif_have_decoder_for_format(HEVC) == 1（libheif-libde265.so 已装载）");

  /* --- 5. 反证：本包未启用其它后端 --- */
  check(heif_have_decoder_for_format(heif_compression_AV1) == 0,
        "heif_have_decoder_for_format(AV1) == 0（无 AV1 后端）");
  check(heif_have_encoder_for_format(heif_compression_HEVC) == 0,
        "heif_have_encoder_for_format(HEVC) == 0（无 HEVC 编码后端）");

  /* --- 6. 宿主 API 可用性：context 生命周期 --- */
  struct heif_context* ctx = heif_context_alloc();
  check(ctx != NULL, "heif_context_alloc() != NULL");
  if (ctx != NULL) {
    heif_context_free(ctx);
  }

  /* --- 7. 反初始化（与 heif_init 引用计数配对） --- */
  heif_deinit();

  printf("LIBSHEIF_LIBDE265_CONSUMER checks_total=%d checks_passed=%d\n",
         checks_total, checks_passed);
  if (checks_passed != checks_total) {
    printf("RESULT: FAIL\n");
    return 1;
  }
  printf("RESULT: PASS\n");
  return 0;
}
