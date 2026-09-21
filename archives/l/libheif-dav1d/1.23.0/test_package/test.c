/* test_package/test.c — libheif-dav1d 1.23.0 消费者契约测试。

本测试是「鸿蒙特有测试」行的唯一来源，全部断言在 test_package 内新写，
不计入上游用例分母（上游用例见 test_package/MANIFEST.yml 与 reports/test-report.md）。

它验证四件事，缺一不可：
  1. 交付面确实存在 —— lib/libheif/libheif-dav1d.so 落盘且是有效 ELF；
  2. 配方导出的运行期插件路径与实际产物目录一致 —— 不能只导出个名字；
  3. 插件确实能被宿主 dlopen 起来 —— heif_init(NULL) 触发宿主扫描并装载插件目录，
     装载失败时 heif_have_decoder_for_format 会返回 0；
  4. 加载后能力面正确 —— AV1 有解码器（dav1d 生效）、HEVC 无解码器、
     AV1 无编码器（dav1d 是纯解码后端，本包不提供 AV1 编码）——
     第 3、4 条合起来排除「别处来的解码器把测试蒙绿」。

关于插件路径为什么要由配方导出：libheif 的搜索顺序（libheif/init.cc:51-66）是
环境变量 LIBHEIF_PLUGIN_PATH 优先、为空才回退编译期宏 LIBHEIF_PLUGIN_DIRECTORY，
而后者是 configure 期的构建目录绝对路径（Conan 装包后会搬到最终缓存目录），
对下载安装的消费者不成立。故 package_info() 用 runenv_info 导出本变量，
本测试经 conanrun 环境取其值，并断言它指向真实产物所在目录。
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "libheif/heif.h"

#ifndef HEIF_PLUGIN_FILE
#define HEIF_PLUGIN_FILE ""
#endif

static int g_total = 0;
static int g_failed = 0;

static void check(int cond, const char* what)
{
    g_total++;
    if (cond) {
        printf("  PASS  %s\n", what);
    } else {
        g_failed++;
        printf("  FAIL  %s\n", what);
    }
}

/* 去掉末尾的 '/'，便于比较目录字符串 */
static void strip_trailing_slash(char* s)
{
    size_t n = strlen(s);
    while (n > 1 && s[n - 1] == '/') {
        s[--n] = '\0';
    }
}

int main(void)
{
    printf("libheif-dav1d consumer contract test\n");
    printf("plugin artifact under test : %s\n", HEIF_PLUGIN_FILE);

    /* ---- 1. 交付面：插件产物存在且是 ELF ---- */
    struct stat st;
    int have_stat = (strlen(HEIF_PLUGIN_FILE) > 0 && stat(HEIF_PLUGIN_FILE, &st) == 0);
    check(have_stat, "lib/libheif/libheif-dav1d.so exists");
    check(have_stat && S_ISREG(st.st_mode) && st.st_size > 0,
          "plugin artifact is a non-empty regular file");

    int elf_magic = 0;
    if (have_stat) {
        FILE* f = fopen(HEIF_PLUGIN_FILE, "rb");
        if (f) {
            unsigned char magic[4] = {0, 0, 0, 0};
            if (fread(magic, 1, 4, f) == 4) {
                elf_magic = (magic[0] == 0x7f && magic[1] == 'E' &&
                             magic[2] == 'L' && magic[3] == 'F');
            }
            fclose(f);
        }
    }
    check(elf_magic, "plugin artifact has ELF magic (loadable object, not a stub)");

    /* ---- 2. 配方导出的运行期插件路径必须存在且指向真实产物目录 ---- */
    const char* env_path = getenv("LIBHEIF_PLUGIN_PATH");
    check(env_path != NULL && strlen(env_path) > 0,
          "recipe exports LIBHEIF_PLUGIN_PATH (baked-in dir is build-time only)");

    int path_matches = 0;
    if (env_path != NULL && strlen(env_path) > 0 && strlen(HEIF_PLUGIN_FILE) > 0) {
        char exported[4096];
        char actual[4096];
        snprintf(exported, sizeof(exported), "%s", env_path);
        snprintf(actual, sizeof(actual), "%s", HEIF_PLUGIN_FILE);
        strip_trailing_slash(exported);
        char* slash = strrchr(actual, '/');
        if (slash != NULL) {
            *slash = '\0';
        }
        strip_trailing_slash(actual);
        path_matches = (strcmp(exported, actual) == 0);
        if (!path_matches) {
            printf("        exported: %s\n        actual  : %s\n", exported, actual);
        }
    }
    check(path_matches, "exported LIBHEIF_PLUGIN_PATH == directory holding the artifact");

    /* ---- 3. 版本与上下文 API ---- */
    const char* version = heif_get_version();
    check(version != NULL && strlen(version) > 0, "heif_get_version() returns a version");
    check(heif_get_version_number_major() == 1 && heif_get_version_number_minor() == 23,
          "heif_get_version_number_major/minor == 1.23");
    check(heif_get_version_number() != 0, "heif_get_version_number() is non-zero");

    struct heif_context* ctx = heif_context_alloc();
    check(ctx != NULL, "heif_context_alloc() succeeds");
    if (ctx) {
        heif_context_free(ctx);
    }

    /* ---- 4. 插件装载与能力面 ---- */
    struct heif_error err = heif_init(NULL);
    check(err.code == heif_error_Ok, "heif_init() scans and loads the plugin directory");

    check(heif_have_decoder_for_format(heif_compression_AV1) == 1,
          "AV1 decoder registered  => libheif-dav1d.so was dlopen'd and is functional");
    check(heif_have_decoder_for_format(heif_compression_HEVC) == 0,
          "HEVC decoder absent     => no other codec backend leaked into this package");
    check(heif_have_encoder_for_format(heif_compression_AV1) == 0,
          "AV1 encoder absent      => dav1d is decode-only, as declared");

    heif_deinit();

    printf("libheif-dav1d consumer contract: %d/%d assertions passed\n",
           g_total - g_failed, g_total);
    if (g_failed != 0) {
        fprintf(stderr, "libheif-dav1d consumer contract FAILED: %d of %d assertions\n",
                g_failed, g_total);
        return 1;
    }
    return 0;
}
